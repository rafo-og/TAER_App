import pyvisa
import time
from statistics import *


class NP1930:
    def __init__(self):
        self.wavelength = 500
        address = "GPIB0::6::INSTR"  # Check
        rm = pyvisa.ResourceManager()
        self.device = rm.open_resource(address)
        self.device.timeout = 1000
        self.device.query_delay = 0.3
        self.reboot()

    def __del__(self):
        self.device.close()

    def close(self):
        self.device.close()

    def reboot(self):
        rebooted = True
        while rebooted:
            try:
                self.reset()
                self.clear_query()
                time.sleep(10)
                self.config()
                rebooted = False
            except Exception as e:
                print("Reboot failed... trying again.")

    def clear_query(self):
        print("Clearing query queue...")
        try:
            self.device.query("RUN")  # Just to receive something and clear the entire queue
            while True:
                self.device.read()
        except Exception as e:
            pass

    def config(self):
        print("Configuring device...")
        ID = self.device.query("*IDN?")
        print(f"ID: {ID}")
        self.device.write("*CLS")  # Clean status register
        self.device.write("AUTO_A 1")  # Set auto range
        self.device.write("BEEP 1")  # Enable beep
        self.set_lambda()

    def reset(self):
        print("Reseting device...")
        self.device.write("*RST")
        time.sleep(5)

    def set_lambda(self, wavelength=None):
        if wavelength != None:
            self.wavelength = wavelength
        self.device.write("LAMBDA " + str(self.wavelength))
        time.sleep(5)

    def check_status(self, code):
        status = 0
        attempts = 0
        self.device.write("*CLS")  # Clean status register
        while (status & code) == 0:
            try:
                status = int(self.device.query("*STB?").replace("\r", ""))
            except Exception as e:
                print("On check status")
                print(e)
                self.check_error()
                attempts = attempts + 1
                if attempts >= 5:
                    self.reboot()
                    attempts = 0
        return True

    def check_error(self):
        try:
            self.clear_query()
            time.sleep(3)
            error = self.device.query("ERR?")
            error_code = int(error.split(",")[0])
            if error_code != 0:
                self.reboot()
        except Exception as e:
            self.reboot()

    def read_power(self, samples=1, sigma=0.01):
        power = []
        power_avg = 0
        not_valid = True
        while not_valid:
            while len(power) < samples:
                try:
                    self.check_status(0x02)  # Check there is new valid measure available
                    power_meas = float(self.device.query("R_A? ").replace("\r", ""))
                    # print(power_meas)
                    power.append(power_meas)
                except Exception as e:
                    print("On read power")
                    print(e)
                    self.check_error()
            if stdev(power) < sigma:
                power_avg = sum(power) / len(power)
                not_valid = False
            else:
                power.clear()
                print("Measure standard deviation to high, repeating...")
        return power_avg


# Testing the script
if __name__ == "__main__":
    np = NP1930()
    # np.set_lambda(600)
    power = np.read_power(10)
    power = power / 100 * 1000000  # W/cm^2 to uW/mm^2
    power = round(power, 5)
    print("Output power: " + str(power) + (" uW/mm2"))
