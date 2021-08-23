INSTALLPATH="/usr/share/ampache-localplay/"
BINPATH="/usr/local/bin/"
APPPATH="/usr/share/applications/"
INSTALLTEXT="Ampache-Localplay has been installed."
UNINSTALLTEXT="Ampache-Localplay has been removed."

install-req:
	# Copy executable
	cp ampache-localplay $(BINPATH) -f
	# Copy shortcut
	cp ampache-localplay.desktop $(APPPATH) -f
	# Make environment
	mkdir -p $(INSTALLPATH)
	cp ampachelocalplay.py $(INSTALLPATH) -f
	cp ampache.py $(INSTALLPATH) -f
	cp main.ui $(INSTALLPATH) -f
	cp LICENSE $(INSTALLPATH) -f
	cp ampache-localplay.png $(INSTALLPATH) -f

install: install-req
	@echo
	@echo $(INSTALLTEXT)

install-gui: install-req
	# Notify graphically
	zenity --info --title='Installation complete' --text=$(INSTALLTEXT)

uninstall-req:
	# Simply remove the installation path folder
	rm -rf $(INSTALLPATH)

uninstall: uninstall-req
	@echo
	@echo $(UNINSTALLTEXT)

uninstall-gui: uninstall-req
	# Notify graphically
	zenity --info --title='Uninstall complete' --text=$(UNINSTALLTEXT)

