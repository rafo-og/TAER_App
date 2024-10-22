import pyvisa
import time


class CORNERSTONE130:
    def __init__(self):
        address = "GPIB0::4::INSTR"  # Check
        rm = pyvisa.ResourceManager()
        self.device = rm.open_resource(address)
        self.device.timeout = 5000
        self.device.query_delay = 0.3
        self.config()

    def config(self):
        # print("Configuring device...")
        # ID = self.device.query('*IDN?')
        # print(f"ID: {ID}")
        pass

    def __del__(self):
        self.device.close()

    def close(self):
        self.device.close()

    def set_lambda(self, wavelength=None):
        if wavelength != None:
            self.wavelength = wavelength
        self.device.write("GOWAVE " + str(self.wavelength))
        time.sleep(5)


# Testing the script
if __name__ == "__main__":
    device = CORNERSTONE130()
    device.set_lambda(700)
    device.set_lambda(500)
    device.set_lambda(450)
