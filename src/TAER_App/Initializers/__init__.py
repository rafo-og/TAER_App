from TAER_App.Initializers.initializer_base import InitializerBase
import os
from inspect import isclass
from pkgutil import iter_modules

package_folder = os.path.dirname(__file__)
# Iterate through the modules in the current package
for importer, module_name, ispkg in iter_modules([package_folder]):
    try:
        # import the module and iterate through its attributes
        module = importer.find_module(module_name).load_module(module_name)
        for attribute_name in dir(module):
            attribute = getattr(module, attribute_name)
            if isclass(attribute) and issubclass(attribute, InitializerBase):
                # Add the class to this package's variables
                globals()[attribute_name] = attribute
    except Exception as e:
        print(e)
