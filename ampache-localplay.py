#!/usr/bin/env python3

"""    Copyright (C)2021
       Lachlan de Waard <lachlan.00@gmail.com>
       ----------------------------------------
       ampache-localplay: json localplay client
       ----------------------------------------

 This program is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.    
    
 This program is distributed in the hope that it will be useful,    
 but WITHOUT ANY WARRANTY; without even the implied warranty of    
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the    
 GNU General Public License for more details.    

 You should have received a copy of the GNU General Public License    
 along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import configparser
import gi
import os

import ampache

gi.require_version('Peas', '1.0')
gi.require_version('PeasGtk', '1.0')

from gi.repository import GObject, Peas, PeasGtk, Gio, Gtk
from xdg.BaseDirectory import xdg_config_dirs

_here = os.path.abspath(os.path.dirname(__file__))
HOMEFOLDER = os.getenv('HOME')
PLUGIN_PATH = '/ampache-localplay/'
CONFIGFILE = xdg_config_dirs[0] + PLUGIN_PATH + 'alp.conf'
UIFILE = os.path.join(_here, 'main.ui')
C = 'conf'


def run_events():
    while Gtk.events_pending():
        Gtk.main_iteration()


class AmpacheLocalplay(GObject.Object, Peas.Activatable, PeasGtk.Configurable):
    __gtype_name__ = 'ampache-localplay'
    object = GObject.Property(type=GObject.Object)

    def __init__(self):
        GObject.Object.__init__(self)
        self.plugin_info = 'ampache-localplay'
        self.conf = configparser.RawConfigParser()
        self.configfile = CONFIGFILE
        self.ui_file = UIFILE
        self.window = None
        self.db = None
        self.player = None
        self.source = None
        self.queue = None
        self.app = None

        self.statusbar = None
        self.tracklabel = None
        self.playlistcombo = None
        self.playlistlist = None
        self.state = 'unknown'
        self.volume = 0
        self.repeat = None
        self.random = None
        self.track = ''
        self.track_title = ''
        self.track_artist = ''
        self.track_album = ''

        # ampache details
        self.ampache_url = None
        self.ampache_user = None
        self.ampache_apikey = None
        self.ampache_session = False
        self.do_activate()

    def do_activate(self):
        """ Activate the plugin """
        print('activating ampache-localplay')
        self._check_configfile()
        # load the main window
        self.do_create_main_window()
        run_events()

    def do_deactivate(self):
        """ Deactivate the plugin """
        print('deactivating ampache-localplay')
        Gio.Application.get_default()
        del self.shell
        del self.rbdb
        del self.db
        del self.player
        del self.source
        del self.queue
        del self.app
        del self.elapsed_changed_id

    def ampache_auth(self, key):
        """ ping ampache for auth key """
        self.ampache_user = self.conf.get(C, 'ampache_user')
        self.ampache_url = self.conf.get(C, 'ampache_url')
        self.ampache_apikey = self.conf.get(C, 'ampache_api')
        if self.ampache_url[:8] == 'https://' or self.ampache_url[:7] == 'http://':
            if key:
                ping = ampache.ping(self.ampache_url, key)
                if ping:
                    # ping successful
                    self.update_status('ping')
                    self.ampache_session = ping
                    return ping
            auth = ampache.handshake(self.ampache_url, ampache.encrypt_string(self.ampache_apikey, self.ampache_user))
            if auth:
                self.update_status('handshake')
                print('handshake successful')
                self.ampache_session = auth
                return auth
        return False

    def _check_configfile(self):
        """ Copy the default config template or load existing config file """
        if not os.path.isfile(self.configfile):
            folder = os.path.split(self.configfile)[0]
            if not os.path.exists(folder):
                os.makedirs(folder)
            """ create a default config if not available """
            conffile = open(self.configfile, "w")
            conffile.write('[conf]\n' +
                           'ampache_url = \n' +
                           'ampache_user = \n' +
                           'ampache_api = \n')
            conffile.close()
        else:
            conf = configparser.RawConfigParser()
            conf.read(self.configfile)
            if not conf.has_section('home'):
                conf.add_section('home')
            if not conf.has_section('root_x'):
                conf.add_section('root_x')
            if not conf.has_section('root_y'):
                conf.add_section('root_y')
            if not conf.has_section('width'):
                conf.add_section('width')
            if not conf.has_section('height'):
                conf.add_section('height')
            # set default path for the user
            self.conf.read(self.configfile)
            datafile = open(self.configfile, 'w')
            self.conf.write(datafile)
            datafile.close()
        # read the conf file            
        self.conf.read(self.configfile)
        return

    def do_create_main_window(self):
        """ Load the glade UI for the config window """
        build = Gtk.Builder()
        build.add_from_file(self.ui_file)
        self._check_configfile()
        self.conf.read(self.configfile)
        self.window = build.get_object('main')
        self.statusbar = build.get_object('statuslabel')
        self.tracklabel = build.get_object('tracklabel')
        self.statelabel = build.get_object('statelabel')
        self.volumelabel = build.get_object('volumelabel')
        self.playlistcombo = build.get_object("playlistcombo")
        self.playlistlist = build.get_object('playlistlist')
        self.window.connect("destroy", self.quit)
        build.get_object('loadbutton').connect('clicked', lambda x: self.play_now())
        build.get_object('refreshbutton').connect('clicked', lambda x: self.localplay_status())
        build.get_object('clearbutton').connect('clicked', lambda x: self.delete_all())
        build.get_object('settingsbutton').connect('clicked', lambda x: self.do_create_config_window())
        build.get_object('previousbutton').connect('clicked', lambda x: self.localplay_previous())
        build.get_object('stopbutton').connect('clicked', lambda x: self.localplay_stop())
        build.get_object('pausebutton').connect('clicked', lambda x: self.localplay_pause())
        build.get_object('playbutton').connect('clicked', lambda x: self.localplay_play())
        build.get_object('nextbutton').connect('clicked', lambda x: self.localplay_next())
        build.get_object('volupbutton').connect('clicked', lambda x: self.localplay_volume_up())
        build.get_object('voldownbutton').connect('clicked', lambda x: self.localplay_volume_down())
        self.playlistcombo.connect("changed", self.playlistchanged)
        # prepare playlist list
        self.playlistcombo.set_model(self.playlistlist)
        self.playlistcombo.clear()
        cell = Gtk.CellRendererText()
        self.playlistcombo.pack_start(cell, False)
        self.playlistcombo.add_attribute(cell, 'text', 1)
        self.getplaylists()
        self.localplay_status()
        
        # check for config file and info
        self.window.show_all()
        self.window.show()
        Gtk.main()

    def do_create_config_window(self):
        """ Load the glade UI for the config window """
        build = Gtk.Builder()
        build.add_from_file(self.ui_file)
        self._check_configfile()
        self.conf.read(self.configfile)
        preferences = build.get_object('preferences')
        build.get_object('closebutton').connect('clicked', lambda x: preferences.destroy())
        build.get_object('savebutton').connect('clicked', lambda x: self.save_config(build))
        build.get_object('ampache_url').set_text(self.conf.get(C, 'ampache_url'))
        build.get_object('ampache_user').set_text(self.conf.get(C, 'ampache_user'))
        build.get_object('ampache_api').set_text(self.conf.get(C, 'ampache_api'))
        preferences.show_all()
        preferences.show()

    def quit(self, *args):
        """ stop the process thread and close the program"""
        self.window.destroy()
        Gtk.main_quit(*args)
        return False

    def set_status(self, text):
        self.statusbar.set_text(text)
        self.tracklabel.set_text(self.track + ' - ' + self.track_title + ' - ' + self.track_album + ' - ' + self.track_artist)
        self.statelabel.set_text(self.state)
        self.volumelabel.set_text(str(int(self.volume * 100)) + '%')
        run_events()

    def save_config(self, builder):
        """ Save changes to the plugin config """
        self.ampache_url = builder.get_object('ampache_url').get_text()
        self.ampache_user = builder.get_object('ampache_user').get_text()
        self.ampache_apikey = builder.get_object('ampache_api').get_text()
        self.conf.set(C, 'ampache_url', self.ampache_url)
        self.conf.set(C, 'ampache_user', self.ampache_user)
        self.conf.set(C, 'ampache_api', self.ampache_apikey)
        datafile = open(self.configfile, 'w')
        self.conf.write(datafile)
        datafile.close()
        self.set_status('Config Saved')
        # Get a session
        self.ampache_auth(self.ampache_session)

    def playlistchanged(self, *args):
        """ traverse folders on double click """
        currentitem = self.playlistcombo.get_active_iter()
        try:
            return self.playlistlist.get_value(currentitem, 0)
        except TypeError:
            return False

    def getplaylists(self):
        if self._check_session():
            self.playlistlist.clear()
            print("refresh playlists")
            status = ampache.playlists(self.ampache_url, self.ampache_session, False, False, 0, 0, 'json')
            for child in status['playlist']:
                self.playlistlist.append([child['id'], child['name']])
            self.localplay_status('refresh')

    def _check_session(self):
        return self.ampache_auth(self.ampache_session)

    def delete_all(self):
        if self._check_session():
            ampache.localplay(self.ampache_url, self.ampache_session, 'delete_all')
            self.update_status('delete_all')

    def play_now(self):
        if self._check_session():
            listid = self.playlistchanged()
            if not listid:
                return False
            status = ampache.playlist_songs(self.ampache_url, self.ampache_session, listid, 0, 0, 'json')
            songs = []
            for child in status['song']:
                songs.append(child['id'])
            self.delete_all()
            count = 0
            for song_id in songs:
                ampache.localplay(self.ampache_url, self.ampache_session, 'add', song_id, 'song', 0)
                if count == 0:
                    self.localplay_play()
                    count = 1
            self.localplay_status('play')

    def localplay_previous(self):
        if self._check_session():
            ampache.localplay(self.ampache_url, self.ampache_session, 'previous')
            self.localplay_status('previous')

    def localplay_stop(self):
        if not self.state == 'stop' and self._check_session():
            ampache.localplay(self.ampache_url, self.ampache_session, 'stop')
            self.localplay_status('stop')

    def localplay_pause(self):
        if not self.state == 'pause' and self._check_session():
            ampache.localplay(self.ampache_url, self.ampache_session, 'pause')
            self.localplay_status('pause')

    def localplay_play(self):
        if not self.state == 'play' and self._check_session():
            ampache.localplay(self.ampache_url, self.ampache_session, 'play')
            self.localplay_status('play')

    def localplay_next(self):
        if self._check_session():
            ampache.localplay(self.ampache_url, self.ampache_session, 'next')
            self.localplay_status('next')

    def localplay_volume_up(self):
        if self.volume < 1.00 and self._check_session():
            ampache.localplay(self.ampache_url, self.ampache_session, 'volume_up')
            self.volume = round(self.volume + .05, 2)
            self.update_status('volume_up')

    def localplay_volume_down(self):
        if self.volume > 0.00 and self._check_session():
            ampache.localplay(self.ampache_url, self.ampache_session, 'volume_down')
            self.volume = round(self.volume - .05, 2)
            self.update_status('volume_down')

    def update_status(self, state=False):
        if not state:
            state = self.state
        self.set_status(state)

    def localplay_status(self, state=False):
        """
          #def localplay(ampache_url: str, ampache_api: str, command, oid=False, otype=False, clear=0, api_format: str = 'xml'):
          #* command     = (string) 'next', 'prev', 'stop', 'play', 'pause', 'add', 'volume_up',
          #                         'volume_down', 'volume_mute', 'delete_all', 'skip', 'status'
        """
        if self._check_session():
            status = ampache.localplay(self.ampache_url, self.ampache_session, 'status')
            self.state = status[0][0][0][0].text
            self.volume = float(int(status[0][0][0][1].text) / 100)
            self.repeat = status[0][0][0][2].text
            self.random = status[0][0][0][3].text
            try:
                if status[0][0][0][4].text and status[0][0][0][5].text:
                    self.track = status[0][0][0][4].text
                    self.track_title = status[0][0][0][5].text
            except IndexError:
                self.track = ''
                self.track_title = ''
            try:
                if status[0][0][0][6].text:
                    self.track_artist = status[0][0][0][6].text
            except IndexError:
                self.track_artist = ''
            try:
                if status[0][0][0][7].text:
                    self.track_album = status[0][0][0][7].text
            except IndexError:
                self.track_album = ''
            self.update_status(state)


if __name__ == "__main__":
    AmpacheLocalplay()
