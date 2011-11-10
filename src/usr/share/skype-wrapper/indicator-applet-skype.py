#!/usr/bin/env python
# -*- coding: latin-1 -*-
#
#Copyright 2010 Andreas Happe
#
#Authors:
#    Andreas Happe <andreashappe@snikt.net>
#    Shannon A Black <shannon@netforge.co.za>
#
#This program is free software: you can redistribute it and/or modify it 
#under the terms of either or both of the following licenses:
#
#1) the GNU Lesser General Public License version 3, as published by the 
#Free Software Foundation; and/or
#2) the GNU Lesser General Public License version 2.1, as published by 
#the Free Software Foundation.
#
#This program is distributed in the hope that it will be useful, but 
#WITHOUT ANY WARRANTY; without even the implied warranties of 
#MERCHANTABILITY, SATISFACTORY QUALITY or FITNESS FOR A PARTICULAR 
#PURPOSE.  See the applicable version of the GNU Lesser General Public 
#License for more details.
#
#You should have received a copy of both the GNU Lesser General Public 
#License version 3 and version 2.1 along with this program.  If not, see 
#<http://www.gnu.org/licenses/>
#


# Documentation:
# just start it

import indicate
import gobject
import gtk
import Skype4Py

import os
import sys
import commands
import time
import dbus

import threading

def do_nothing(indicator):
    True
    
    
AppletRunning = True
    
CB_INTERVALS = 5000

FOCUSDEBUG = 4
ERROR = 3
WARNING = 2
INFO = 1

LOGTYPES = {
    0:"",
    1:"INFO: ",
    2:"WARNING: ",
    3:"ERROR: ",
    4:"DEVELOPER DEBUG: ",
}

# only display errors
LOGLEVEL = INFO

def log(message, level):
    if level >= LOGLEVEL:
        print LOGTYPES[level] + message

# this is the high-level notification functionality
class NotificationServer:
  def __init__(self):
    self.server = indicate.indicate_server_ref_default()
    self.server.set_type("message.im")
#   this is kinda ugly, or?
    self.server.set_desktop_file("/usr/share/applications/skype-wrapper.desktop")
    self.server.show()
    self.indicators = {}
    pass

  def connect(self, skype):
    self.skype = skype
    self.server.connect("server-display", self.on_click)

  def on_click(self, server,data=None):
    self.skype.skype.Client.Focus()
   
  def show_conversation(self, indicator, timestamp):
    log("Display skype chat and remove missed chat from indicator", INFO)
    
    id = indicator.get_property("id")
    indicator_name = indicator.get_property("indicator_name")

    self.skype.remove_conversation(int(id))
    self.skype.show_chat_windows(int(id))
    
    del self.indicators
    for _id in self.skype.unread_conversations:
        if not self.skype.unread_conversations[int(id)].Read:
            self.show_indicator(self.skype.unread_conversations[int(id)])

  def show_indicator(self, conversation):      
    log("Updating Indicator", INFO)
    new = False
    if not conversation.indicator_name in self.indicators:
        self.indicators[conversation.indicator_name] = indicate.Indicator()
        self.indicators[conversation.indicator_name].set_property_bool("draw-attention", True)    
        self.indicators[conversation.indicator_name].set_property("id", str(conversation.id))
        self.indicators[conversation.indicator_name].set_property("indicator_name", str(conversation.indicator_name))
        self.indicators[conversation.indicator_name].connect("user-display", self.show_conversation)
        new = True
    self.indicators[conversation.indicator_name].set_property("name", str(conversation.display_name))    
    self.indicators[conversation.indicator_name].set_property("timestamp", str(conversation.timestamp))
    self.indicators[conversation.indicator_name].set_property_time('time', conversation.timestamp)
    if new:
        self.indicators[conversation.indicator_name].show()
    return
    
    
  def user_online_status(self, username, fullname, online_text):
    log("User "+username+" "+online_text, INFO)
    if username == 'echo123':
        return
        
    avatar = SkypeAvatar(username)
    
    if not fullname:
        fullname = username
        
    if avatar.filename:
        os.system('notify-send -i "'+avatar.filename+'" "'+fullname+'" "'+online_text+'"');
    else:
        os.system('notify-send -i "/usr/share/skype/avatars/Skype.png" "'+fullname+'" "'+online_text+'"');
  
  def new_message(self, conversation):
    group_chat_title = unicode(conversation.skypereturn.Sender.FullName + " → " + conversation.skypereturn.Chat.Topic)
    avatar = SkypeAvatar(conversation.skypereturn.Sender.Handle)
    fullname = conversation.skypereturn.Sender.FullName
    if not fullname:
        fullname = username
    
    if avatar.filename:
        os.system(u'notify-send -i "'+avatar.filename+'" "'+group_chat_title+'" "'+conversation.skypereturn.Body+'"');
    else :
        os.system(u'notify-send -i "/usr/share/skype/avatars/Skype.png" "'+group_chat_title+'" "'+conversation.skypereturn.Body+'"');

# class for retrieving user avatars
class SkypeAvatar:
  def __init__(self, username):
    userfiles = {
        "user256", 
        "user1024", 
        "user4096", 
        "user16384", 
        "user32768", 
        "user65536",
        "profile256", 
        "profile1024", 
        "profile4096", 
        "profile16384", 
        "profile32768"
    }
    
    path = os.getenv("HOME")+"/.thumbnails/normal/"
    skypedir = os.getenv("HOME")+"/.Skype/"+skype.skype.CurrentUser.Handle+"/"
    
    self.image_data = ""
    self.filename = ""
    
    skbin = []
    n = 0
    for f in userfiles:
        fil = "%s%s.dbb" % (skypedir, f)
        try: skbin.append(file(fil, "rb").read())
        except: pass
        n = n + 1
        
    binary = "".join(skbin)
    self.get_icon(username, binary)
    if len(self.image_data) :
        f = open(path+"skype-wrapper-"+username+".jpg", mode="w")
        f.write(self.image_data)
        f.close()
        self.filename = path+"skype-wrapper-"+username+".jpg"
        log("Wrote avatar to file "+self.filename, INFO)
        
    return
    
  def get_icon(self, buddy, binary):
    startmark = "\xff\xd8"
    endmark = "\xff\xd9"

    startfix = 0
    endfix = 2

    nick_start = "\x03\x10%s" % buddy
    nick_end = "\x6C\x33\x33\x6C"

    nickstart = binary.find(bytes(nick_start))
    if nickstart == -1: return -1
    log("Found avatar for "+buddy, INFO)
    
    nickend = binary.find(nick_end, nickstart)
    handle = binary[nickstart+2:nickend]
    blockstart = binary.rfind("l33l", 0, nickend)
    imgstart = binary.find(startmark, blockstart, nickend)
    imgend = binary.find(endmark, imgstart)

    imgstart += startfix
    imgend += endfix

    if (imgstart < startfix): 
        return None
    ##print "JPG %s from %d to %d" % (handle, imgstart, imgend)
    self.image_data = binary[imgstart:imgend]
    return True
    

class Conversation:
  def __init__(self, display_name, timestamp, skype_id, mesg):
    self.id = mesg.Id
    self.display_name = display_name
    self.skypereturn = mesg
    self.count = 0
    self.timestamps = [timestamp]
    self.timestamp=timestamp
    self.indicator_name = mesg.Chat.Name
    self.Read = False
    
    
  def add_timestamp(self, timestamp):
    self.timestamps.append(timestamp)
    self.count += 1

class SkypeBehaviour:
  # initialize skype
  def __init__(self):
    log("Initializing Skype API", INFO)
    self.skype = Skype4Py.Skype()
    self.skype.Client.Start(Minimized=True)

    log("Waiting for Skype Process", INFO)
    while True:
      output = commands.getoutput('ps -A | grep skype' )
      if 'skype' in output.replace('skype-wrapper', ''):
        break

    log("Attaching skype-wrapper to Skype process", INFO)
    time.sleep(4)
    while True:
        try:
            self.skype.Attach(Wait=True)
            break
        except:
            print "."
                        
    log("Attached complete", INFO)
    time.sleep(2)
    self.skype.Client.Minimize()
    self.name_mappings = {}
    self.unread_conversations = {}
    
    # we will store all outdated messages here, anything not here will get net notified
    self.conversations = {}
    
    # store all the users online for notifying if they're on
    self.usersonline = {}
    
    self.cb_show_conversation = None
    self.cb_show_indicator = None
    self.cb_user_status_change = None
    self.cb_log_message = None
    
    #self.initOnlineUserList()
    gobject.timeout_add(CB_INTERVALS, self.checkUnreadMessages)
    gobject.timeout_add(CB_INTERVALS, self.checkOnlineUsers)

  def SetShowConversationCallback(self, func):
    self.cb_show_conversation = func

  def SetShowIndicatorCallback(self, func):
    self.cb_show_indicator = func
    
  def SetUserOnlineStatusChangeCallback(self, func):
    self.cb_user_status_change = func
    
  def SetNewMessageCallback(self, func):
    self.cb_log_message = func

  def remove_conversation(self, id):
    #skype_name = self.name_mappings[display_name]
    #self.unread_conversations[display_name].skypereturn.Seen = True
    #del self.unread_conversations[id]
    display_name = self.unread_conversations[int(id)].display_name
    for _id in self.unread_conversations:
        if display_name == self.unread_conversations[int(_id)].display_name:
            self.unread_conversations[int(_id)].Read = True
    self.unread_conversations[int(id)].Read = True
    return
   
  def logMessage(self, conversation):
    if not conversation:
        return
    id = conversation.id
    if not id in self.conversations:
        log("Logging Message", INFO)
        self.conversations[id] = conversation
        if self.cb_log_message:
            self.cb_log_message(conversation)
    return
   
  def initOnlineUserList(self) :
    if self.skype.Friends:
        for friend in self.skype.Friends:
            if not friend.Handle in self.usersonline:
                if friend.OnlineStatus != "OFFLINE":
                    self.usersonline[friend.Handle] = friend.FullName
    return
   
  def checkOnlineUsers(self) :
    log("Checking online status changing users", INFO)
    #check who is now offline
    for friend in self.usersonline:
        for skypefriends in self.skype.Friends:
            if skypefriends.OnlineStatus == "OFFLINE" and friend == skypefriends.Handle:
                del self.usersonline[skypefriends.Handle]
                if self.cb_user_status_change:
                        self.cb_user_status_change(skypefriends.Handle, skypefriends.FullName, "went offline")
    
    #check who is now online
    if self.skype.Friends:
        for friend in self.skype.Friends:
            if not friend.Handle in self.usersonline:
                if friend.OnlineStatus != "OFFLINE":
                    self.usersonline[friend.Handle] = friend
                    if self.cb_user_status_change:
                        self.cb_user_status_change(friend.Handle, friend.FullName, "is online")
    
    return AppletRunning
  
  def checkUnreadMessages(self):
    log("Checking unread messages", INFO)
    missedmessages = []
    if self.skype.MissedMessages:
        for mesg in self.skype.MissedMessages:
            missedmessages.append(mesg)
            
    if missedmessages and self.cb_show_indicator:
       for mesg in reversed(missedmessages):
         id = mesg.Id
         display_name = mesg.Chat.FriendlyName
      
         if not id in self.unread_conversations:
             conversation = Conversation(display_name, mesg.Timestamp, mesg.Sender.Handle, mesg)
             self.name_mappings[id] = mesg.Sender.Handle
             self.unread_conversations[id] = conversation
         else:
             self.unread_conversations[id].add_timestamp(mesg.Timestamp)
         
         self.logMessage(self.unread_conversations[id])
         if not self.unread_conversations[id].Read:
            self.cb_show_indicator(self.unread_conversations[id]) 
    return AppletRunning

  def show_chat_windows(self, id):
    self.unread_conversations[id].skypereturn.Chat.OpenWindow()
  

def runCheck():
    log("Check if Skype instance is running", INFO)
    #print self.skype.Client.IsRunning
    #calling self.skype.Client.IsRunning crashes. wtf. begin hack:
    output = commands.getoutput('ps -A | grep skype' )
    
    if 'skype' not in output.replace('skype-wrapper',''):
        log("Skype instance has terminated, exiting", WARNING)
        gtk.main_quit()
    if 'defunct' in output:
        log("Skype instance is now defunct, exiting badly", ERROR)
        gtk.main_quit()
        
    return AppletRunning

if __name__ == "__main__":

  os.chdir('/usr/share/skype-wrapper')
  
  skype = SkypeBehaviour();
  server = NotificationServer()
  gobject.timeout_add(CB_INTERVALS, runCheck)
  
  skype.SetShowConversationCallback(server.show_conversation)
  skype.SetShowIndicatorCallback(server.show_indicator)
  skype.SetUserOnlineStatusChangeCallback(server.user_online_status)
  skype.SetNewMessageCallback(server.new_message)
  
  server.connect(skype)
  
  #workaround_show_skype()

  # why is this needed?
  #server.activate_timeout_check()

  # check for newly unread messages..
  #skype.check_timeout(server)
  gtk.main()
  AppletRunning = False
