# TAER APP

Application for AER-based sensors testing. 


## How to install the TAER APP

We recomend to use Visual Studio Code to work with this project. Open a new empty folder in the IDE and follow these steps (it is assumed that Python 3.10.5 is installed on the system):

1. Open a terminal in the created empty folder where the app will be hosted.
21. Create a virtual python environment: <code>python -m venv .venv</code>. This will create a folder named <code>.venv</code>
3. Activate the virtual environment: <code>.venv\Scripts\activate</code>
4. Upgrade the package manager <code>pip</code> to the last version: <code>python -m pip install --upgrade pip</code>
5. Install the required Python modules in editable mode: <code>python -m pip install -e .</code>
6. The app uses the Opal Kelly board libraries (FrontPanel library). These libraries are propietary and must be downloaded by each user using their own serial number. Once the OK libraries are downloaded, copy the following files to <code>.venv/Lib/site-packages</code>:
    - _ok.pyd
    - ok.py
    - okFrontPanel.dll
    - okFrontPanel.lib
7. Open and launch the <code>app.py</code> script to launch the app. The application can be launch in debug mode also.

## How to add a new chip to the app

To configure a new chip to work with this application, two steps must be followed: create a new configuration file in the [chip_configs](src/TAER_App/chip_configs) folder and a new initializer script in the [Initializers](src/TAER_App/Initializers) folder.

### Creating a configuration file

The first step is to copy the file [config_template.yaml](src/TAER_App/chip_configs/config_template.yaml) in the same folder and replace the name with a meaningful one. Once we have copied these files we need to replace some configuration parameters regarding the sensor architecture to be added. The configuration has three main sections: SENSOR, MODEL and VIEW.

#### SENSOR

This section defines the sensor resolution through the X and Y parameters. In the template, the X and Y parameters take the value 64 as default. It must be modified as needed.

Also the 'chip_name' is defined in this section. This name should be unique for your chip in case more than one configuration coexists in the [chip_configs](src/TAER_App/chip_configs) folder.

#### MODEL

The following table specifies the default values and the function of each parameter in this section.

|        PARAMETER        	| FUNCTION                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  	| DEFAULT VALUE 	|
|:-----------------------:	|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------	|:-------------:	|
| ```operation_timeout``` 	| It's the maximum time that the app will wait to receive an image from the sensor. This should be modified regarding the settings in the Opal Kelly board.                                                                                                                                                                                                                                                                                                                                                                                                              	|       30      	|
|       ```rotate```      	| Image rotation. The accepted values are: "R0", "R90", "R180", "R270"                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      	|     "R90"     	|
|        ```flip```       	| Image mirroring. The accepted values are: "None", "MX" and "MY".                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          	|      "MX"     	|
|       ```modes```       	| This section defines the operating modes performed by the sensor. The modes are defined through a list containing the name of the mode (the label) and the code which identifies the mode. This code is used in the Opal Kelly board to enable the corresponding signals and modules.                                                                                                                                                                                                                                                                                     	|       -       	|
|  ```device_registers``` 	| This parameter contains a list of registers defined in the Opal Kelly board. Each element on the list is a register defined by its label, the address defined in the OK and the default value it takes.                                                                                                                                                                                                                                                                                                                                                                    	|       -       	|
|        ```dacs```       	| Contains a list of DACs implemented in the test board. Currently, the supported DAC is the device DAC124S085.                                                                                                                                                                                                                                                                                                                                                                                                                                                             	|       -       	|
|        ```adcs```       	| Defines a list of ADCs channels available in the test board. Currently, the supported ADC is the device MCP3204T-CI/ST. A label and calibration data (slope and offset) is assigned to each channel.                                                                                                                                                                                                                                                                                                                                                                      	|       -       	|
|     ```adc_tmeas```     	| Time between ADC samples.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 	|       -       	|
|   ```chip_registers```  	| This parameter contains a list of registers implemented onto the chip if exists. We usually define a bank of registers accessible through communication standards such as SPI or UART. Each register is defined by its label and its address. Also, inside each register, the user can define signals indicating as a list the label of the signal, the first bit of the signal and the width of the signal. Refer to the examples for further details.                                                                                                                      	|       -       	|
| ```tools```             	| Define a list of tools used in the app. Currently, there are two tools available: the multiplexer selector and the PCB switch selector. The behaviour of each tool can be modified regarding three flags: enable, update chip and update device. The first is to enable the tool for the current configuration, the second to indicate if the tool modifies the values of the chip registers and the last one if the tool modifies the values of the OK. The two last parameters should be kept as is and they are only used in case a new tool is implemented in the future. 	| -             	|


#### VIEW

This section configures aspects regarding the GUI. The ```main_panel_size``` sets the size of the main window. The user can modify it as needed. The other parameters must remain as they are.

### Creating a New Initializer File

The folder [Initializers](Initializers) contains an initializer for each configured chip. To create a new initializer, the user must copy the file [initializer_template.py](Initializers/initializer_template.py) into the same folder and replace the name with a meaningful one. The first thing to be done is to change the [line 48](Initializers/initializer_template.py#L48) specifying the same chip name set in the configuration file (the value in the template for this attribute is `"chip_template"`). This attribute links the initializer with the corresponding configuration file.

The initializer defines a series of methods that will be called in the app flow. The user can perform any task needed for a specific application in these code snippets. The app data is available through the model instance (i.e. `self.model`). These are the methods that should be defined in the initializer as a minimum (i.e. you can define your own here too):

- `def on_start_app(self):` This method is executed at the beginning of the application lifetime. It can serve tasks like setting default configuration values.

- `def on_close_app(self):` The code in this method is executed when the user closes the app.

- `def on_init_capture(self):` This code is executed before the capture loop is launched. For instance, it can serve to enable a clock before the sensor operation starts.

- `def on_before_capture(self):` This code is executed in the capture loop and just before the capture command is sent to the OK board.

- `def on_after_capture(self, raw_data):` This code is executed in the capture loop and just after the capture command is sent to the OK board and the app has received the data from the sensor. The received data is contained in the input argument `raw_data` as a numpy array of bytes. This method is used to format your data regarding the needs of the specific chip. The result of formatting the data should be assigned to `self.model.main_img_data`, and depending on the kind of data the user returns, the app behaviour changes:

  - If the type of data is different from `"uint8"`, the app will convert the data to this type through a linear conversion.
  - If the shape of the array is different from the resolution defined in the configuration file, the app will reshape it (and perform trimming if needed) to agree with the sensor resolution.
  - If the colour mapping is different from `cv.COLOR_GRAY2BGR`, the app will convert the data through the `cv.cvtColor` method.
  - If the data fulfils all the requirements listed before (i.e. it is in `"uint8"` type, with the required shape and the mapping corresponds to `cv.COLOR_GRAY2BGR`), the image will be displayed as it is, without any modification. Thus, the data can be represented as the user needs.

- `def on_end_capture(self):` This code is executed after the capture loop ends. For instance, it can serve to disable a clock after the sensor operation ends.

- `def on_test(self):` This code is executed when the user clicks on `Tools > Execute test`. It serves as a starting point to execute specific tests for the chip. For instance, it can trigger multimeter measures, light sweeps, or any other test that you need to perform with your sensor.

- `def gen_serial_frame(self, operation: str, register: ChipRegister):` and `def parse_serial_frame(self, data: list, register: ChipRegister) -> list:` These methods perform the formatting/parsing to send/receive data over a serial protocol. The default configuration is implemented for SPI communication but can be modified as needed to implement other kinds of protocols such as UART.

## App architecture

This section is not really necessary to read, it is intended for those who want to have a deeper understaing of the app architecture. The app is composed of two main modules: TAER_Core and TAER_App. TAER_Core contains the core of the application and it is not intended to be accessible to app users, it should only be modified by app developers. On the other hand, TAER_App module is contained in this repository and can be modified regarding to the user needs. For further reference, please follow this link to the [TAER_Core](https://github.com/rafo-og/TAER_Core) repository.

## License

This project is licensed under the GNU General Public License v3.0 (GPLv3).

You are free to use, modify, and distribute this software, but any derivative works must also be open source and licensed under GPLv3. Please retain attribution to the original project and author.
