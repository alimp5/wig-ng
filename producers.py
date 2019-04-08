#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# wig-ng - Wireless Information Gathering New Generation
# Copyright (C) 2019 - Andrés Blanco (6e726d) <6e726d@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from multiprocessing import Process, Event

import pcapy

from helpers import radiotap

# Link-Layer Headre Types
# https://www.tcpdump.org/linktypes.html
DLT_IEEE802_11 = 105
DLT_IEEE802_11_RADIO = 127


class LiveNetworkCapture(Process):
    """
    Live Network Capture produccer class objective is to capture network traffic
    from a network interface and put it a queue.
    """

    SNAPLEN = 65535
    PROMISC = True
    TIMEOUT = 100  # in miliseconds

    def __init__(self, network_interface, frames_queue, bpf_filter=None):
        Process.__init__(self)
        self.__network_interface__ = network_interface
        self.__frames_queue__ = frames_queue
        self.__filter__ = bpf_filter
        self.__stop__ = Event()
        self.__ieee80211_frame_offset__ = None
        self.__open_network_interface__()
        self.__set_ieee80211_frame_offset__()

    def __open_network_interface__(self):
        """
        This method opens the network interface and sets the BPF filter. 
        """
        self.__pd__ = pcapy.open_live(self.__network_interface__,
                                      self.SNAPLEN,
                                      self.PROMISC,
                                      self.TIMEOUT)
        if self.__filter__:
            self.__pd__.setfilter(self.__filter__)

    def __set_ieee80211_frame_offset__(self):
        """
        This method sets the offset for the IEEE 802.11 frame data. We are not
        using the Radiotap header. In case we have a datalink that has Radiotap
        we need to process at least one frame to get the Radiotap length.
        """
        datalink = self.__pd__.datalink()
        if datalink == DLT_IEEE802_11:
            self.__ieee80211_frame_offset__ = 0
        elif datalink == DLT_IEEE802_11_RADIO:
            while True:
                _, frame = self.__pd__.next()  # Ignore metadata header
                if frame:
                    self.__ieee80211_frame_offset__ = radiotap.get_length(frame)
                    break
        else:
            msg = "%s is not a wireless interface." % self.__network_interface__
            raise ValueError(msg)

    def run(self):
        """
        This method reads frames from the pcap file descriptor and put them
        into the frame queue.
        """
        while not self.__stop__:
            _, frame = self.__pd__.next()  # Ignore metadata header
            if frame:
                buff = frame[self.__ieee80211_frame_offset__:]
                self.__frames_queue__.put(buff)

    def shutdown(self):
        """
        This method sets the __stop__ event to stop the process.
        """
        self.__stop__.set()


class OfflineNetworkCapture(Process):
    """
    Offline Network Capture produccer class objective is to read network traffic
    from a pcap file and put it a queue.
    """
    def __init__(self, pcap_filename, frames_queue, bpf_filter=None):
        Process.__init__(self)
        self.__pcap_filename__ = pcap_filename
        self.__frames_queue__ = frames_queue
        self.__filter__ = bpf_filter
        self.__stop__ = Event()
        self.__ieee80211_frame_offset__ = None
        self.__open_pcap_file__()
        self.__set_ieee80211_frame_offset__()

    def __open_pcap_file__(self):
        """
        This method opens the pcap network capture file and sets the BPF filter. 
        """
        self.__pd__ = pcapy.open_offline(self.__pcap_filename__)
        if self.__filter__:
            self.__pd__.setfilter(self.__filter__)

    def __set_ieee80211_frame_offset__(self):
        """
        This method sets the offset for the IEEE 802.11 frame data. We are not
        using the Radiotap header. In case we have a datalink that has Radiotap
        we need to process at least one frame to get the Radiotap length.
        """
        datalink = self.__pd__.datalink()
        if datalink == DLT_IEEE802_11:
            self.__ieee80211_frame_offset__ = 0
        elif datalink == DLT_IEEE802_11_RADIO:
            while True:
                _, frame = self.__pd__.next()  # Ignore metadata header
                if frame:
                    self.__ieee80211_frame_offset__ = radiotap.get_length(frame)
                    break
        else:
            msg = "%s is not a wireless interface." % self.__pcap_filename__
            raise ValueError(msg)

    def run(self):
        """
        This method reads frames from the pcap file descriptor and put them
        into the frame queue.
        """
        while not self.__stop__:
            _, frame = self.__pd__.next()  # Ignore metadata header
            if frame:
                buff = frame[self.__ieee80211_frame_offset__:]
                self.__frames_queue__.put(buff)

    def shutdown(self):
        """
        This method sets the __stop__ event to stop the process.
        """
        self.__stop__.set()
