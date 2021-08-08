class WrongPraatioVersion(Exception):
    pass


raise WrongPraatioVersion(
    "\n\nWARNING: You've tried to import 'tgio' which was renamed 'textgrid' in praatio 5.x.\n"
    "Many other, breaking changes were made.\n"
    "You will need to modify your code to use praatio 5.0.\n"
    "If you would like to use your code without changes, please run the following "
    "two instructions from the command line to install praatio 4.x:\n\n"
    "pip uninstall praatio\n"
    "pip install 'praatio<5'"
)
