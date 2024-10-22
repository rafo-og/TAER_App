import pyvisa
import time


class HP4155A:
    def __init__(self):
        address = "GPIB0::17::INSTR"  # Check
        rm = pyvisa.ResourceManager()
        self.device = rm.open_resource(address)
        self.device.timeout = 5000
        self.device.write("*RST")  # If it does not work, check "write_ascii_values"
        self.id = self.device.query("*IDN?")
        self.__setup_device()

    def __del__(self):
        self.device.close()

    def sweep_voltage(self, Vstart, Vstop, Vstep, Imax, mode="MED"):
        # Number of steps: (Vmax-Vmin)/Vstep+1 < 255
        if not (mode == "SHOR" or mode == "MED" or mode == "LONG"):
            print("ERROR. Valid modes are: 'SHOR': no oversampling. 'MED': 16 samples. 'LONG': 256 samples.")
        elif Vstart > Vstop:
            print("ERROR. Vstop must be GREATER than Vstart")
        else:
            n_points = int((Vstop - Vstart) / Vstep) + 1  # Number of points
            n_sweeps = int(n_points / 512) + 1  # Number of sweeps
            V_sweep = (Vstop - Vstart) / n_sweeps  # Voltage sweep range in each sweep
            Vstart_i = Vstart  # Start voltage of sweep "i"
            Vstop_i = Vstart_i + V_sweep  # Stop voltage of sweep "i"
            # First sweep
            [data_Vk, data_Ik, data_Va, data_Ia] = self.__sweep_var1(Vstart_i, Vstop_i, Vstep, Imax, mode)
            n_sweeps = n_sweeps - 1
            while n_sweeps > 0:
                Vstart_i = Vstop_i
                Vstop_i = Vstop_i + V_sweep
                if Vstop_i > Vstop:
                    Vstop_i = Vstop
                data_meas = self.__sweep_var1(Vstart_i, Vstop_i, Vstep, Imax, mode)
                data_Vk = ",".join([data_Vk, data_meas[0]])
                data_Ik = ",".join([data_Ik, data_meas[1]])
                data_Va = ",".join([data_Va, data_meas[2]])
                data_Ia = ",".join([data_Ia, data_meas[3]])
                n_sweeps = n_sweeps - 1
            return [data_Vk, data_Ik, data_Va, data_Ia]

    def __setup_device(self):
        # This function setups "SMU2" as common and "SMU3" as "VAR1"
        self.device.write(":PAGE:CHAN")
        self.device.write(":PAGE:CHAN:ALL:DIS")  # Delete settings of all units
        self.device.write(":PAGE:CHAN:MODE SWEEP")
        self.device.write(":PAGE:CHAN:SMU2:FUNC CONS")  # Constant
        self.device.write(":PAGE:CHAN:SMU2:INAME 'IA'")
        self.device.write(":PAGE:CHAN:SMU2:VNAME 'VA'")
        self.device.write(":PAGE:CHAN:SMU2:MODE V")
        self.device.write(":PAGE:CHAN:SMU3:FUNC VAR1")  # Variable to sweep
        self.device.write(":PAGE:CHAN:SMU3:INAME 'IK'")
        self.device.write(":PAGE:CHAN:SMU3:VNAME 'VK'")
        self.device.write(":PAGE:CHAN:SMU3:MODE V")  # Voltage output mode

    def __setup_sweep(self, Vstart, Vstop, Vstep, Imax, mode="MED"):
        # Units: Imax -> A
        #        Vx   -> V
        # MODES: "SHOR", "MED" (16 samples) "LONG" (256 samples)
        self.device.write(":PAGE:MEAS:VAR1:COMP " + "10mA")  # str(Imax))       # Compliance
        self.device.write(":PAGE:MEAS:CONS:SMU2:COMP " + "-" + str(Imax))  # Compliance
        self.device.write(":PAGE:MEAS:CONS:SMU2:SOUR 0")  # Anode voltage
        self.device.write(":PAGE:MEAS:VAR1:MODE SING")  # Single stair
        self.device.write(":PAGE:MEAS:VAR1:SPAC LIN")  # Spacing (LIN, L10, L25 or L50)
        self.device.write(":PAGE:MEAS:VAR1:STAR " + str(Vstart))
        self.device.write(":PAGE:MEAS:VAR1:STOP " + str(Vstop))
        self.device.write(":PAGE:MEAS:VAR1:STEP " + str(Vstep))
        # Stop condition (only when initial interval > 2ms)
        # self.device.write(":PAGE:MEAS:SAMP:SCON ON")                # Enable stop condition
        # self.device.write(":PAGE:MEAS:SAMP:SCON:NAME 'IK'")
        # self.device.write(":PAGE:MEAS:SAMP:SCON:THR "+ str(Imax))   # Ith
        # self.device.write(":PAGE:MEAS:SAMP:SCON:EVENT HIGH")        # If Ik > Ith stops the sweep
        self.device.write(":PAGE:MEAS:SSTop COMP")  # Stop sweep if some SMU reaches its compliance setting
        # Measure conditions
        self.device.write(":PAGE:MEAS:MSET:SMU2:RANG:MODE AUTO")
        self.device.write(":PAGE:MEAS:MSET:SMU3:RANG:MODE AUTO")
        self.device.write(":PAGE:MEAS:MSET:ITIM:MODE " + mode)

    def __setup_display(self, Vmin, Vmax, Imax):
        self.device.write(":PAGE:DISP:GRAP:X:MAX " + str(Vmax))
        self.device.write(":PAGE:DISP:GRAP:X:MIN " + str(Vmin))
        self.device.write(":PAGE:DISP:GRAP:X:SCAL LIN")
        self.device.write(
            ":PAGE:DISP:GRAP:Y1:SCAL LOG"
        )  # In most cases, using a log scale for the current is more convenient
        self.device.write(":PAGE:DISP:GRAP:Y1:MAX " + str(Imax))
        self.device.write(":PAGE:DISP:GRAP:Y1:NAME 'IK'")
        self.device.write(":PAGE:DISP:GRAP:Y1:MIN 1fA")  # Edit this if you expect negative current
        self.device.write(
            ":PAGE:DISP:GRAP:Y2:SCAL LIN"
        )  # In most cases, using a log scale for the current is more convenient
        self.device.write(":PAGE:DISP:GRAP:Y2:NAME 'IA'")
        self.device.write(":PAGE:DISP:GRAP:Y2:MAX 1fA")  # Edit this if you expect negative currents
        self.device.write(":PAGE:DISP:GRAP:Y2:MIN " + "-" + str(Imax))
        # self.device.write("PAGE:DISP:LIST 'VK','IK','VA','IA")

    def __meas_data(self, mode="MED"):
        self.device.write(":PAGE:SCON:MEAS:SING")  # Single measure
        state = self.device.query(":PAGE:SCON:STAT?")
        while state == "MEAS\n":
            time.sleep(1)
            state = self.device.query(":PAGE:SCON:STAT?")
        Vk = self.device.query(":TRAC? VK")
        Va = self.device.query(":TRAC? VA")
        Ik = self.device.query(":TRAC? IK")
        Ia = self.device.query(":TRAC? IA")
        return [Vk, Ik, Va, Ia]

    def __sweep_var1(self, Vstart, Vstop, Vstep, Imax, mode="MED"):
        # Setting up sweep parameters
        self.__setup_display(Vstart, Vstop, Imax)
        self.__setup_sweep(Vstart, Vstop, Vstep, Imax, mode)
        data_meas = self.__meas_data(mode)
        return data_meas


# Testing the script
if __name__ == "__main__":
    device = HP4155A()
    # Test
    # [Vk, Ik, Va, Ia] = device.sweep_voltage(0, 0.520, 0.001, '1mA','SHOR')
    [Vk, Ik, Va, Ia] = device.sweep_voltage(17, 20, 0.01, "1mA", "SHOR")
    pass
