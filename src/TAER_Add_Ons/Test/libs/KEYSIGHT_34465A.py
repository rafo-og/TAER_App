import pyvisa
import time


class KEYSIGHT_34465A:
    def __init__(self) -> None:
        rm = pyvisa.ResourceManager()
        # Get the first resource connected through USB
        resource_list = rm.list_resources()
        self.dev_addr = None
        for resource in resource_list:
            if "USB" in resource.split("::")[0]:
                self.dev_addr = resource
                break
        if self.dev_addr is None:
            raise Exception("Resource not found.")
        self.ctrl = rm.open_resource(self.dev_addr)
        self.reset()
        self.clear()
        self.cfg_dc_amp()
        self.cfg_dc_amp_range(1)
        time.sleep(1)
        self.info = self.ctrl.query("*IDN?")

    def print_info(self):
        infos = self.info.split(",")
        print("Device info:")
        for info in infos:
            print(f"\t{info}")

    def print_ondisplay(self, string):
        cmd = f'DISP:TEXT "{string}"'
        self.ctrl.write(cmd)

    def clear_display(self):
        cmd = "DISPlay:TEXT:CLEar"
        self.ctrl.write(cmd)

    def clear(self):
        self.info = self.ctrl.write("*CLS")

    def reset(self):
        self.ctrl.write("*RST;")

    def cfg_dc_amp(self):
        cmd = "CONF:CURR:DC"
        self.ctrl.write(cmd)
        cmd = "CURR:APER:ENAB ON"
        self.ctrl.write(cmd)
        cmd = "CURR:DC:APER 1E-03;TERM 3"
        self.ctrl.write(cmd)
        cmd = "CURR:SWIT:MODE CONT"
        self.ctrl.write(cmd)

    def cfg_dc_amp_range(self, range):
        range_str = "{:.2e}".format(range).replace("e", "E")
        cmd = f"CURR:DC:RANG {range_str}"
        self.ctrl.write(cmd)
        time.sleep(0.5)

    def trig_dc_amp_meas(self, samples, delay):
        self.ctrl.write("TRIG:SOUR BUS")
        cmd = f"SAMP:COUN {samples}"
        self.ctrl.write(cmd)
        cmd = f"TRIG:COUN 1"
        self.ctrl.write(cmd)
        self.ctrl.write("INIT")
        self.ctrl.write("*TRG")

    def read_dc_amp_meas(self, maxAttemps=10):
        success = False
        attemps = 0
        mstr = None
        while not success:
            c = self.ctrl.query("STAT:OPER:COND?")
            c = self.__gpib_str_conv(c)
            if not (c & 16):
                try:
                    mstr = self.ctrl.query("FETC?", delay=1)
                except Exception as e:
                    print(repr(e))
                    attemps = attemps + 1
                    if attemps == maxAttemps:
                        break
                    time.sleep(0.1)
                else:
                    success = True
            else:
                time.sleep(0.1)
        if mstr is None:
            res = None
        else:
            res = self.__gpib_str_conv(mstr)
        return res

    def __gpib_str_conv(self, str):
        str = str.replace("\n", "").replace("+", "")
        if "," in str:
            data = str.split(",")
            f = [self.__gpib_sel_num_type(r) for r in data]
        else:
            f = self.__gpib_sel_num_type(str)
        return f

    def __gpib_sel_num_type(self, str):
        if "." in str:
            return float(str)
        else:
            return int(str)


# The USB SCPI address is 'USB0::0x2A8D::0x0101::MY60086215::INSTR'

if __name__ == "__main__":
    dev = KEYSIGHT_34465A()
    dev.print_info()
    dev.cfg_dc_amp()
    dev.trig_dc_amp_meas(100, 1)
    meas = dev.read_dc_amp_meas()
    print(meas)
