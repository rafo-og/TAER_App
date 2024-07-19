from TAER_Add_Ons.Initializers.initializer_base import InitializerBase
from TAER_Core.main_model import MainModel
from TAER_Core.Libs import LINK_VALUE_DEF, TRIGGER_DEF
import numpy as np
import time
import cv2 as cv
from io import StringIO
import multiprocessing
import os


class InitializerSaer(InitializerBase):
    def __init__(self, model: MainModel) -> None:
        super().__init__(model)
        self.chip_name = "chip_saer"
        self.controller = SaerController()
        self.spad_voltage = 20  # V. Set here the bias voltage of SPADs (refer to Controller -> Supply -> 'enable_vspad')
        # Output file configuration
        self.save_rawdata = False  # Set to true to save raw data. A checkbox might be included to modify this file
        self.output_prefix = ""  # Add a prefix for output files if desired
        self.output_path = "output_files"

    def on_start_app(self):
        # reg_res = self.controller.supply.read_res_reg(model)
        # model.device.program("test/saer/bitstreams/AER_TOP.bit")
        pass

    def on_close_app(self):
        self.controller.supply.disable_vspad(self.model)  # Disable VSPAD
        pass

    def on_init_capture(self):
        time.sleep(0.01)
        self.new_file = True
        self.controller.delay.reset_delay(self.model)
        self.controller.supply.enable_vspad(self.spad_voltage, self.model)

        div_current = self.model.read_dev_register("SRAM DIV DIN")
        self.controller.reset_mask(div_current, self.model)

        self.controller.sram.write_sram_global(self.model)

        self.__set_mode_from_name()
        self.n_frames = 0
        self.bin = 0

        ## UNCOMMENT to disable screamers
        # self.controller.read_mask_dcr("test/saer/dcr_map_2.txt", self.model)

        ## UNCOMMENT TO ISLATE SINGLE PIXEL
        # pixel con DCR 784
        # self.controller.isolate_pixel(1, 2, 7, self.model)  # CHECK DIV!!

    def on_before_capture(self):
        if self.model.current_mode == 0x01:  # TFS
            self.controller.sram.write_sram_global(self.model)

    def on_after_capture(self, raw_data):
        if self.save_rawdata:
            self.__save_raw_img(
                raw_data,
                os.path.join(self.output_path, self.output_prefix),
                self.new_file,
            )
            self.new_file = (
                False  # To avoid creating infinite files when recording a video
            )

        ## TOF: capture 1e4 frames and increase 4 caps
        # self.n_frames = self.n_frames + 1
        # if (self.n_frames > 0):
        #     self.n_frames = 0
        #     self.bin = self.bin + 1
        #     self.controller.delay.increase_delay(4, self.model)
        # if (self.bin > 255):
        #     print("FINISHED")
        # else:
        #     with open("test/saer/tof/fine/" + str(self.bin)+".txt", "a+") as f:
        #         np.savetxt(f, np.int32(raw_data))

        if self.model.current_mode == self.model.modes["Raw data"]:
            im_out = self.reconstruct_events(raw_data[0:10000])  # COMMENT THIS THIS
            self.model.main_img_data = im_out
        elif self.model.current_mode == self.model.modes["pDVS"]:
            im_out = self.reconstruct_events_pdvs(raw_data[0:10000])
            self.model.main_img_data = im_out
        else:
            im_out = np.copy(raw_data.astype("float32"))
            im_out[raw_data > 0] = np.log10(raw_data[raw_data > 0])
            im_out = (im_out - np.min(im_out)) / (np.max(im_out) - np.min(im_out)) * (2**8 - 1)
            self.model.main_img_data = np.uint16(im_out)
            print("Events: " + str(self.model.device.actions.get_evt_count()))

    def on_end_capture(self):
        self.n_frames = 0
        # self.save_time()
        self.controller.supply.disable_vspad(self.model)  # Disable VSPAD
        self.model.device.actions.reset_aer()

    def gen_serial_frame(self, mode, register):
        self.model.device.actions.enable_clk_chip(True)
        data = None
        if mode == "write":
            n_bytes = np.ceil(register.size / 8).astype(int).item()  # number of bytes to be sent
            bytes_tx = list(register.value.to_bytes(n_bytes, "big"))
            data = [
                (register.address & 0x3F | 0x40),
                n_bytes * 8,
            ] + bytes_tx  # cosas de ruben
        elif mode == "read":
            data = [(register.address & 0x3F | 0x80), register.size]
            data = data + [0] * (np.ceil(register.size / 8).astype(int).item() + 1)
        else:
            self.logger.error("Operation not allowed.")
        return data

    def parse_serial_frame(self, serial_data, register):
        self.model.device.actions.enable_clk_chip(False)
        n_bytes = len(serial_data)
        reg_size = np.ceil(register.size / 8).astype(int).item()
        data_bytes = serial_data[(n_bytes - reg_size) : :]
        data_out = int.from_bytes(data_bytes, "big")
        return data_out

    def __set_mode_from_name(self):
        mode_name = self.model.get_current_mode_name(self.model.current_mode)
        if mode_name == "Raw data" or mode_name == "pDVS" or mode_name == "QI RAW":
            self.model.FR_raw_mode_en = True
        else:
            self.model.FR_raw_mode_en = False

    def save_image(self, data_in, path):
        with open(path, "ab") as f:
            np.savetxt(f, data_in)

    def __save_raw_img(self, img, filename, new_file=True):
        if new_file:
            self.output_filename = self.__create_new_filename(filename)

        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(self.output_filename, "w") as f:
            img.tofile(f)  # To recover the info use fromfile function

    def __create_new_filename(self, path):
        mode = self.model.current_mode
        if mode == 0x00:
            name = "FR"
        elif mode == 0x01:
            name = "TFS"
        elif mode == 0x02:
            name = "QI_FRAME"
        elif mode == 0x03:
            name = "TOF"
        elif mode == 0x04:
            name = "EVENTS"
        elif mode == 0x06:
            name = "PDVS"
        elif mode == 0x07:
            name = "QI_EVENTS"
        filename, extension = os.path.splitext(path)
        filename = filename + name
        path = filename + extension
        counter = 1
        while os.path.exists(path):
            path = filename + "_" + str(counter) + extension
            counter += 1
        return path + ".bin"

    def append_raw_data(self, data_in, path, chunk_size=100 * (2**20)):
        with open(path, "ab+", buffering=chunk_size) as file:
            for chunk in data_in:
                file.write(chunk)

    def save_time(self):
        path = "test/saer/results_nerpio/time.txt"
        # t_ntp = self.ntp_client.request(self.ntp_server)
        with open(path, "a+") as file:
            """
            file.write("delay: " + str(t_ntp.delay)+"\n")
            file.write("dest_time: " + str(t_ntp.dest_time)+"\n")
            file.write("dest_timestamp: " + str(t_ntp.dest_timestamp)+"\n")
            file.write("offset: " + str(t_ntp.offset)+"\n")
            file.write("orig_time: " + str(t_ntp.orig_time)+"\n")
            file.write("orig_timestamp: " + str(t_ntp.orig_timestamp)+"\n")
            file.write("recv_time: " + str(t_ntp.recv_time)+"\n")
            file.write("recv_timestamp: " + str(t_ntp.recv_timestamp)+"\n")
            file.write("ref_time: " + str(t_ntp.ref_time)+"\n")
            file.write("ref_timestamp: " + str(t_ntp.ref_timestamp)+"\n")
            file.write("tx_time: " + str(t_ntp.tx_time)+"\n")
            file.write("tx_timestamp: " + str(t_ntp.tx_timestamp)+"\n\n")
            """
            file.write(str(time.time()) + "\n")

    def reconstruct_events(self, raw_data):
        im_out = np.zeros([64, 64])
        addresses = raw_data[0::2]
        for x in range(64):
            for y in range(64):
                addr_pix = (y << 16) + x
                im_out[y, x] = np.sum(addresses == addr_pix)
        return im_out

    def reconstruct_events_pdvs(self, raw_data):
        im_out = np.zeros([64, 64])
        addr_all = raw_data[0::2]  # These include intensity and motion events
        events = addr_all >> 24
        addr = addr_all[events == 1]  # Filtering motion events
        sign = (addr >> 16) & 0xFF
        sign = np.int32(sign) * 2 - 1  # Detecting sign
        addr = addr & 0x0FFFF
        for x in range(64):
            for y in range(64):
                addr_pix = (y << 8) + x
                idx = addr == addr_pix
                im_out[y, x] = np.sum(sign[idx])

        n_min = -np.min(im_out)
        n_max = np.max(im_out)

        if n_max > n_min:
            im_out = (im_out / n_max) * 127 + 127
        else:
            im_out = (im_out / n_min) * 127 + 127

        return im_out

    def write_chunk_to_file(self, args):
        filename, chunk = args
        with open(filename, "ab+") as file:
            file.write(chunk)

    def write_large_data_to_file_parallel(self, filename, data, num_processes=4):
        pool = multiprocessing.Pool(processes=num_processes)
        chunk_size = len(data) // num_processes
        chunked_data = [data[i : i + chunk_size] for i in range(0, len(data), chunk_size)]
        args_list = [(filename, chunk) for chunk in chunked_data]
        pool.map(self.write_chunk_to_file, args_list)
        pool.close()
        pool.join()


class SaerController:
    def __init__(self) -> None:
        self.sram = SaerSram()
        self.delay = SaerDelay()
        self.supply = SaerSupply()
        self.img_mask = 7 * np.ones(64 * 64, np.int8)

    def save_image(self, model: MainModel):
        image = model.main_img

    def reset_mask(self, init, model: MainModel):
        self.img_mask = init * np.ones(64 * 64, np.int8)

    def set_mask(self, mask, model: MainModel):
        self.img_mask = mask

    def adapt_mask(self, event_rate, tol, model: MainModel):
        image_last = np.copy(model.main_img_data)
        self.update_image(self.img_mask, model)

        evts = np.sum(image_last)
        if evts > 10e6 * 0.03:  # If saturation happens
            self.reset_mask(0, model)
            model.write_dev_register("SRAM DIV DIN", 0)
            self.sram.write_sram_global(model)
        else:
            idx = np.where((image_last > event_rate * (1 + tol)))
            self.img_mask[idx] = self.img_mask[idx] - 1

            idx = np.where(image_last < event_rate * (1 - tol))
            self.img_mask[idx] = self.img_mask[idx] + 1
            # idx = np.where((image_last == 0))
            # self.img_mask[idx] = self.img_mask[idx] - 1

            idx = np.where(self.img_mask > 7)
            self.img_mask[idx] = 7
            idx = np.where(self.img_mask < 0)
            self.img_mask[idx] = 0

            self.update_mask(model)

    def update_mask(self, model: MainModel):
        mask_array = np.reshape(self.img_mask, [64, 64], "C")
        self.sram.write_sram(mask_array.tolist(), model)

    def update_image(self, mask_array, model: MainModel):
        coef_array = np.copy(mask_array)
        coef_array = np.invert(coef_array)
        coef_array = np.bitwise_and(coef_array, 0x07)
        with open("test/saer/tof/adaptive.txt", "ab") as f:
            np.savetxt(f, model.main_img_data)
        with open("test/saer/tof/coef.txt", "ab") as f:
            np.savetxt(f, coef_array)
        model.main_img_data = np.left_shift(model.main_img_data, coef_array)

    def isolate_pixel(self, x, y, ndiv, model: MainModel):
        mask_iso = 8 * np.ones(64 * 64, np.int8)
        mask_iso[64 * x + y] = ndiv
        self.set_mask(mask_iso, model)
        self.update_mask(model)

    def read_mask_dcr(self, file, model: MainModel):
        data = np.loadtxt(file, dtype=int)
        n_div = model.read_dev_register("SRAM DIV DIN")
        mask = n_div * np.ones(64 * 64, dtype=int)
        mask[data > 10] = 8
        self.set_mask(mask, model)
        self.update_mask(model)


class SaerSram:
    def __reset_array(self, model: MainModel):
        model.write_signal("en_online_ram_data", 1)
        model.device.actions.enable_clk_chip(True)
        model.device.actions.write_serial([19, 4, 255, 19, 4, 100])
        time.sleep(0.001)  # wait reset action
        model.device.actions.enable_clk_chip(False)

    def write_sram_global(self, model: MainModel):
        model.write_signal("en_online_ram_data", 1)
        model.device.actions.set_aux_signal(1, 1)
        model.device.actions.enable_clk_chip(True)
        model.device.actions.write_serial([20, 1, 20, 10, 19, 16, 3, 255, 255])
        time.sleep(0.0001)
        model.device.actions.write_serial([20, 0xFF])
        model.device.actions.enable_clk_chip(False)
        model.device.actions.set_aux_signal(1, 0)

    def write_sram(self, data, model: MainModel):  # Data should be a 64x64 matrix (list of lists)
        model.write_signal("en_online_ram_data", 0)
        data = list(zip(*data))  # now data[i] represents column data

        self.__start_writing(model, "even")  # Writing 64 columns (starting at even rows)
        for i in range(64):
            data_col = data[i][i % 2 :: 2]
            data_col = list(
                map(self.__mask_data, data_col, [0x0F] * len(data_col))
            )  # We avoid the user specifies a value out of range
            self.__write_sram_reg(data_col, model)
            self.__write_sram_col(model)
        self.__stop_writing(model)

        self.__start_writing(model, "odd")  # Writing 64 columns (starting at odd rows)
        for i in range(64):
            data_col = data[i][(i + 1) % 2 :: 2]
            data_col = list(
                map(self.__mask_data, data_col, [0x0F] * len(data_col))
            )  # We avoid the user specifies a value out of range
            self.__write_sram_reg(data_col, model)
            self.__write_sram_col(model)
        self.__stop_writing(model)

        model.write_signal("en_online_ram_data", 1)

    def write_sram_rowmask(self, n_rows, value, model: MainModel):
        model.write_signal("en_online_ram_data", 0)
        mask = np.append(
            value * np.ones(64 * n_rows, np.uint8),
            8 * np.ones(64 * (64 - n_rows), np.uint8),
        )
        data = np.reshape(mask, [64, 64], "C")
        data = data.tolist()
        data = list(zip(*data))

        # self.__start_writing(model, "even") # Writing 64 columns (starting at even rows)
        data_col = data[1][0::2]
        data_col = list(
            map(self.__mask_data, data_col, [0x0F] * len(data_col))
        )  # We avoid the user specifies a value out of range
        self.__write_sram_reg(data_col, model)

        model.device.actions.set_aux_signal(1, 1)
        model.device.actions.enable_clk_chip(True)
        model.device.actions.write_serial([20, 1, 20, 10, 19, 16, 3, 255, 255])
        time.sleep(0.0001)
        model.device.actions.write_serial([20, 0xFF])
        model.device.actions.enable_clk_chip(False)
        model.device.actions.set_aux_signal(1, 0)

        # for i in range(64):
        #     self.__write_sram_col(model)
        # self.__stop_writing(model)

        # self.__start_writing(model, "odd") # Writing 64 columns (starting at odd rows)
        # data_col = data[0][1::2]
        # data_col = list(map(self.__mask_data, data_col, [0X0F]*len(data_col))) # We avoid the user specifies a value out of range
        # self.__write_sram_reg(data_col, model)
        # for i in range(64):
        #     self.__write_sram_col(model)
        # self.__stop_writing(model)

        model.write_signal("en_online_ram_data", 1)

    def __write_sram_reg(self, data_col, model: MainModel):
        a = list(map(self.__mask_data, data_col, [0x01] * len(data_col)))
        sram0 = self.__parse_sram_data(data_col, 0)
        sram1 = self.__parse_sram_data(data_col, 1)
        sram2 = self.__parse_sram_data(data_col, 2)
        sram3 = self.__parse_sram_data(data_col, 3)
        # Escribir señales en chip
        model.write_signal("sram_din0", sram0)
        model.write_signal("sram_din1", sram1)
        model.write_signal("sram_din2", sram2)
        model.write_signal("sram_din3", sram3)

    def __start_writing(self, model: MainModel, first_row="even"):
        if first_row == "even":
            data_spi = [20, 0]
        elif first_row == "odd":
            data_spi = [20, 0, 20, 10, 20, 2]
        else:
            print("ERROR. 'first_row' argument must be either 'even' or 'odd'.")
        model.device.actions.enable_clk_chip(True)
        model.device.actions.write_serial(data_spi)
        model.device.actions.enable_clk_chip(False)

    def __stop_writing(self, model: MainModel):
        model.device.actions.enable_clk_chip(True)
        model.device.actions.write_serial([20, 0x0F, 0xFF])
        model.device.actions.enable_clk_chip(False)

    def __write_sram_col(self, model: MainModel):
        model.device.actions.enable_clk_chip(True)
        model.device.actions.write_serial([20, 10])
        model.device.actions.write_serial([20, 20, 20, 2])
        model.device.actions.enable_clk_chip(False)

    def __parse_sram_data(self, data, bit):  # Hay que darl e la vuelta (0 1 1) escr
        col_bits = list(map(self.__mask_data, data, [2**bit] * len(data)))
        col_bits = list(map(lambda x, offset: x >> offset, col_bits, [bit] * len(data)))
        sram_data = 0
        col_bits.reverse()
        for bit in col_bits:
            sram_data = (sram_data << 1) | (bit & 0x01)
        return sram_data

    def __mask_data(self, n, mask):
        return n & mask


class SaerDelay:
    def reset_delay(self, model: MainModel, mode=0):
        model.device.actions.enable_clk_chip(True)
        if mode == 0:
            model.device.actions.write_serial([85, 128])  # First byte {2'b10, 6'd21}. Second byte: {2'b10, 6'd0}
        else:
            model.device.actions.write_serial([85, 192])  # First byte {2'b10, 6'd21}. Second byte: {2'b11, 6'd0}
        model.device.actions.enable_clk_chip(False)

    def increase_delay(self, inc, model: MainModel):
        model.device.actions.enable_clk_chip(True)
        spi_data_tx = [85, 64 + inc]
        model.device.actions.write_serial(spi_data_tx)
        model.device.actions.enable_clk_chip(False)

    def decrease_delay(self, inc, model: MainModel):
        model.device.actions.enable_clk_chip(True)
        model.device.actions.write_serial([85, 0 + inc])
        model.device.actions.enable_clk_chip(False)

    def read_delay_reg(self, model: MainModel):
        model.device.actions.enable_clk_chip(True)
        data_spi = model.device.actions.write_serial([149, 0, 0, 0])  # If modification is included
        time.sleep(0.0002)  # Waiting for RX data to be received
        data_spi = model.device.actions.read_serial()
        data_reg_delay = data_spi[3] + (data_spi[2] << 8)
        return data_reg_delay


class SaerSupply:
    def __init__(self) -> None:
        pass

    def __send_spi_res(self, address, cmd, data_reg, model: MainModel):
        # Masking data
        address = address & 0x0F
        cmd = cmd & 0x03
        data_reg = data_reg & 0xFF
        spi_data = (address << 12) | (cmd << 10) | data_reg
        model.device.actions.__set_wire__(0x05, spi_data, LINK_VALUE_DEF(0, 15))
        model.device.actions.__update_wires__()
        model.device.actions.__set_trigger__(model.device.actions.links.trig_in, TRIGGER_DEF(10))
        time.sleep(0.001)
        data_rx = model.device.actions.__read_wire__(0x24, LINK_VALUE_DEF(0, 15))  # Check error
        return data_rx

    def write_res_reg(self, data, model: MainModel):
        self.__send_spi_res(0x00, 0x00, data, model)

    def read_res_reg(self, model: MainModel):
        return self.__send_spi_res(0x00, 0x03, 0, model)

    def enable_vspad(self, voltage, model: MainModel):
        if voltage >= 20.2:
            dn = 17
        elif voltage >= 19.2:
            dn = 18
        elif voltage >= 18.2:
            dn = 19
        elif voltage >= 17.5:
            dn = 20

        self.write_res_reg(17, model)
        time.sleep(0.05)
        model.device.actions.set_pcb_switch(0, 1)  # Enable DC-DC
        time.sleep(0.02)
        model.device.actions.set_pcb_switch(1, 1)  # Enable LDO
        time.sleep(0.02)

    def disable_vspad(self, model: MainModel):
        model.device.actions.set_pcb_switch(1, 0)  # Disable LDO
        time.sleep(0.02)
        model.device.actions.set_pcb_switch(0, 0)  # Disable DC-DC
        time.sleep(0.02)
