from TAER_Add_Ons.Initializers.initializer_base import InitializerBase
from TAER_Core.main_model import MainModel, ChipRegister


"""
    THIS FILE IS A TEMPLATE, FOLLOW INSTRUCTIONS BELOW TO BUILD YOUR PROJECT.

    Iniatilizers include several functions that are called during the operation flow of the acquisition process, i.e., when pressing
    'capture' (one shot) or 'start' (video) buttons. The user can define how data
    is controlled in any of them, either configuring the chip or processing output data. These functions are:

        -'on_start_app': This function is executed only once at the beginning of the application. It might be useful if you want to
        program the chip at start up.

        -'on_stop_app': This function is executed only once when the application is closed. It is useful if you want to turn off any
        feature on your system.

        -'on_init_capture': This function is executed only once at the beginning of the acquisition. You can power your system in
        this phase.

        -'on_before_capture': This function is executed whenever a new acquisition is taking place. E.g., if the application is
        capturing video after pressing 'start' button, the app will return to to this phase before the acquisition of the next frame

        -'on_after_capture': Thus function is executed after data is acquired. The function receives a list named 'raw_data' including
        data in the format defined by the opeartion mode and the FPGA. E.g.: in frame mode, data will be an array of MxN elements,
        while in raw mode (also called event mode), data is an array where odd elements are addresses followed by timestamps at even
        elements. Refer to the FPGA for more information. In this state you MUST update the value of 'model.main_img_data' to update
        the image. Refer to 'Model attributes' below for more information.

        -'on_end_capture': This function is executed only once at the end of the operation, being equivalent to 'on_init_capture'.
        You can turn your system off in this step.

        -'on_test': This is an auxiliar function where you can define specific tests for your appliaction. You can for example run
        a set of acquisitions sweeping a parameter of your circuit or you can trigger specific actions that are not contemplated
        in the application.

    These functions use the 'model' to control data and actions during operation.

        -'main_img_data': This attribute stores the
        -'current_mode': This attribute stores

"""


class InitializerTemplate(InitializerBase):  # NAME YOUR CLASS AS DESIRED
    def __init__(self, model: MainModel) -> None:
        super().__init__(model)
        self.chip_name = "chip_template"

    def on_start_app(self):
        print(f"On init application {self.model.current_mode}")

    def on_close_app(self):
        print(f"On close application {self.model.current_mode}")

    def on_init_capture(self):
        print(f"On init capture {self.model.current_mode}")

    def on_before_capture(self):
        print(f"On before capture {self.model.current_mode}")

    def on_after_capture(self, raw_data):
        """
        self.model.main_img_data must be updated to update the image. You can use 1D or 2D
        array as it will be reshaped if required.

        Data in 'raw_data' depends on the mode:
            -If 'self.model.FR_raw_mode_en == False', a frame is expected in the SDRAM of the
            Opal Kelly board, and N*M memory addresses are read out. Otherwise, events are
            readout when 'N_EVENTS' (FPGA) are received. 'raw_data' contains then 2 * N_EVENTS
            values (timestamps and addresses in even and odd positions, respectively)
        """
        # self.model.main_img_data = raw_data # Example
        print(f"On after capture {self.model.current_mode}")

    def on_end_capture(self):
        print(f"On end capture {self.model.current_mode}")

    def on_test(self):
        pass

    ################ DEFAULT IMPLEMENTATION (OPTIONAL, REMOVE IF NOT MODIFIED) ###########################################################################
    # Examples below are the default implementations for SPI serial communication                                                                        #
    #       - gen_serial_frame must generate a byte array containing the data to be transmitted in little endian order. data[0] is transmitted first.    #
    #       - parse_serial_frame receives a byte array in little endian format and must decode the content as you require                                #
    ######################################################################################################################################################
    def gen_serial_frame(self, operation: str, register: ChipRegister):
        """Generate the SPI data frame to send depending on several parameters

        Args:
            operation (str): It could be \"write\" or \"read\"
            mode (int): It represents different protocols to communicate with the chip over SPI. Currently, only mode 1 and mode 2 are defined.
            register (ChipRegister): An object with all the data related with the register properties

        Returns:
            numpy array: The data frame to send over SPI
        """
        # The default operation consists of a SPI interface that sends the address of the register to be written. MSB = 1 for writting.
        # E.g.: Writing 0x3C to register 0x17 -> TX = {0x17 | 0x80, 0x3C}
        # E.g.: Reading register 0x17 -> TX = {0x17, 0x3C}
        self.model.device.actions.enable_clk_chip(True)  # Enable clock before the serial operation
        data = None
        if operation == "write":
            data = [(register.address & 0x7F) | 0x80, register.value]
        elif operation == "read":
            data = [(register.address & 0x7F), 0]
        else:
            self.logger.error("Operation not allowed.")
        return data

    def parse_serial_frame(self, data: list, register: ChipRegister) -> list:
        """Parse the incoming data from SPI depending on several parameters

        Args:
            data (list): The data to parse
            mode (int): It represents different protocols to communicate with the chip over SPI. Currently, only mode 1 and mode 2 are defined.
            register (ChipRegister): An object with all the data related with the register properties

        Returns:
            list: The parsed data
        """
        # The default operation consists of a SPI interface that returns the register value after receiving the address in the first byte
        # E.g.: Reading register 0x17 -> TX = {0x17, 0x00} -> RX = {0x00, DATA}
        self.model.device.actions.enable_clk_chip(False)
        if len(data) > 1:
            return data[1]
        else:
            return []
