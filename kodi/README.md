This directory contains the tools to build a Kodi addon for zap2xml.

This must be run on a Linux machine (tested on Xubuntu 14.0.4LTS)

To build the addon simply type ./build_kodi_addon in this directory.

This addon is designed for use as a replacement for the perl xmltv apps that are dificult/impossible to use on an OpenELEC
distro because perl is not available.

Using the addon:

1) Move the tools.module.zap2xml-<version>.zip to your OpenELEC machine using whatever method you are the most comfortable with.
2) Navigate to SYSTEM->Addons->Install from zip
    == use the file browser to navigate to the file and select it.
3) Navigate to SYSTEM->Addons->My Addons->Program Addons->zap2xml
4) Select Configure and set your Zap2It Username and Password.
5) Reboot the machine
6) Congigure your tv backend to use tv_grab_zap2xml

Notes:

