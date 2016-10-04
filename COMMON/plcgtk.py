#! /usr/bin/env python
# -*- coding: UTF-8 -*-
"""
This module contains a collection of common plcgtk  classes.

Author: JH PLC-Service / MCE / +49 (8669) 31-3102 / service.plc@heidenhain.de
"""

PLC_GTK_VERSION = '6.3'

# IMPORT MODULS
#-----------------------------------------------------------
import pygtk
pygtk.require('2.0')
import gtk          # gtk functions

import pyjh         # JH interface, version
pyjh.require('3.4')
import jh           # import jh interface for event loop
import jh.gtk       # jh.gtk class incl. window-registration
import jh.gtk.glade # import jh glade interface
import jh.pango     # jh.pango fonts
import pango        # pango fonts

import sys          # system functions
import re
import shutil
import gobject      # global objects

from common.get_text import bindTextDomain   # function to set the path and the domain for translation
from common.get_text import txt              # function to translate a text
from common.dialog import *
from common import JhTable

from common.plcSymbolDefinitions  import *

# GLOBAL DEFINITIONS
#-----------------------------------------------------------
GLOBAL_SYMBOL       =  '\\PLC\\program\\symbol\\global\\'
JH_RES_PATH_TOKEN = ['PLC:','TNC:','SYS:','%OEM']
# CLASS
#-----------------------------------------------------------
class embeddedWindow(object):
    """
    This class returns a class with a jh.gtk.window widget.

    Parameter
        usage       : Name of the embedded windows. PLCsmall, PLCmedium, PLClarge .
        title       : Window title.
        logo        : logo for header. output left to the title
        focus       : The window gets the focus.
        setTransient: set the window transient to the NC screen
        padding     : Padding betwen the window frame and the widgets.
        plcSymbol   : Show window plc symbol, connect (M) or None.
        notify      : callbackfunktion that get the notification of the new plcSymbol value.
        styleName   : Widgets can be named, which allows you to refer to them in a GTK resource file
        width       : Window width if the window is not embedded (usage == '')
        height      : Window height if the window is not embedded (usage == '')
        xPos        : Window x position if the window is not embedded (usage == '')
        yPos        : Window y position if the window is not embedded (usage == '')
    """
    instanceCounter = 0

    def __init__(self,usage='PLCmedium', title='PLC WINDOW', logo = None, focus = False, setTransient=True, padding = 1, plcSymbol = None, notify = None, styleName = 'embeddedWindowHeader',width=None,height=None,xPos=None,yPos=None):
        embeddedWindow.instanceCounter += 1
        #print 'INFO %s.%s() <%s> [%s]' %(type(self).__name__, sys._getframe().f_code.co_name, plcSymbol, embeddedWindow.instanceCounter)

        self.usage          = usage
        self.title          = title
        self.logo           = logo
        self.focus          = focus
        self.setTransient   = setTransient
        self.padding        = padding
        self.plcSymbol      = plcSymbol
        self.notify         = notify
        self.width          = width
        self.height         = height
        self.xPos           = xPos
        self.yPos           = yPos

        self.window         = None
        self.firstChild     = None
        self.identPlcSymbol = None
        self.handlePlcSymbol= None

        # define the window style
        gtk.rc_parse( './layout/oemGtkStyle.rc'  )

        #self.set_border_width(5)

        #create the widgets
        self.ScrolledWindow = gtk.ScrolledWindow(hadjustment=None, vadjustment=None)
        self.ScrolledWindow.set_policy(hscrollbar_policy=gtk.POLICY_AUTOMATIC, vscrollbar_policy=gtk.POLICY_AUTOMATIC)

        self.Viewport = gtk.Viewport()
        self.Viewport.set_shadow_type(gtk.SHADOW_OUT)

        self.VBox = gtk.VBox(homogeneous=False, spacing=0)
        self.HBox = gtk.HBox(homogeneous=False, spacing=10)

        self.headerEventBox = gtk.EventBox()
        if styleName:
            self.headerEventBox.set_name(styleName)

        self.headerHBox = gtk.HBox(homogeneous=False, spacing=0)

        if self.logo:
            image = gtk.Image()
            if self.logo[:4] in JH_RES_PATH_TOKEN:
                self.logo = jh.ResPath(self.logo)

            image.set_from_file(self.logo)
            #self.set_alignment(0.0, 0.0)
            image.set_padding(xpad = 1, ypad = 1)

            self.headerHBox.pack_start(image, expand = False, fill = False, padding = 0)

        if self.title:
            titleLabel = gtk.Label(title)
            titleLabel.set_alignment(0.0, 0.5)
            titleLabel.set_padding(xpad = 3, ypad = 0)

            #titleLabel.set_property( 'xalign' , 0 )
            if styleName:
                titleLabel.set_name(styleName)
            self.headerHBox.pack_start(titleLabel, expand = False, fill = False, padding = 0)

        if self.logo or self.title:
            self.headerEventBox.add(self.headerHBox)
            self.pack_start(self.headerEventBox, padding = 1)

        self.HBox.pack_start(self.VBox, padding = self.padding)
        self.Viewport.add(self.HBox)
        self.ScrolledWindow.add(self.Viewport)

        self.firstChild = self.ScrolledWindow

        # subscribe to plc symbol or show the window immediately
        if self.plcSymbol:
            self.identPlcSymbol = GLOBAL_SYMBOL + self.plcSymbol
            self.handlePlcSymbol = jh.Subscribe(ident=self.identPlcSymbol, notify=self._onPlcSymbolChanged, onChange=True)
            if self.handlePlcSymbol is None:
                msg = 'ERROR: can not subscribe to plc symbol %s' %self.identPlcSymbol
                regHandle = MsgReg( plcTextMsgId = 'ERR_SUBSCRIBE',auxMsg=msg)
                if regHandle is not None: raiseHandle = jh.event.Raise( regHandle )
        else:
            self._showWindow()

    def __del__(self):
        """ destructor """
        #print 'INFO %s.%s() <%s> [%s]' %(type(self).__name__, sys._getframe().f_code.co_name, self.plcSymbol, embeddedWindow.instanceCounter)
        embeddedWindow.instanceCounter -= 1

    def _onPlcSymbolChanged(self, plcValueDict, event=None):
        """
        This method runs when the plc symbol changed the value
        """
        #print 'INFO %s::%s() data:%s' %(__name__, sys._getframe().f_code.co_name, plcValueDict)
        newValue = plcValueDict.values()[0]

        if newValue == True:
            self._showWindow()
        else:
            self._destroyWindow()

        if self.notify and callable(self.notify):
            self.notify( newValue )

    def _showWindow(self):
        """
        Create a new jh.gtk.window and add the childs into.
        Then show all.
        """
        self._destroyWindow()

        if self.window == None:
             self.window = jh.gtk.Window(usage=self.usage,setTransient=self.setTransient )
             self.window.set_title('')
             self.window.window.set_functions( gtk.gdk.FUNC_MOVE | gtk.gdk.FUNC_RESIZE | gtk.gdk.FUNC_MINIMIZE | gtk.gdk.FUNC_MAXIMIZE | gtk.gdk.FUNC_CLOSE)

             self.window.connect( 'destroy', self._destroyWindow )

             self.window.add( self.firstChild)

             if self.usage=='':
                 if self.xPos is not None and self.yPos is not None:
                     self.moveWindow( self.xPos, self.yPos )

                 if self.xPos is not None and self.yPos is not None:
                     self.resizeWindow( self.width, self.height )

        self.window.show_all( )

        if self.focus == True:
            self.getFocus()

    def _destroyWindow(self, widget=None):
        """
        Remove the child from the window and destroy the window
        """
        if widget is None:
            if self.window:
                child = self.window.get_child()
                if child:
                    self.window.remove(child)
                self.leaveFocus()
                self.window.destroy()
                self.window = None
        else:
            child = widget.get_child()
            if child:
                self.window.remove(child)

            jh.Put({self.identPlcSymbol : False})

    def changeUsage(self, usage):
        """
        change the usage of the window
        """
        windowWasDisplayed = False
        if self.window:
            windowWasDisplayed = True

        if windowWasDisplayed: self._destroyWindow()
        self.usage = usage
        if windowWasDisplayed: self._showWindow()

    def addSeparator(self, padding = 2):
        """
        Add a separator to
        """
        self.pack_start(gtk.HSeparator(), padding=padding )

    def pack_start(self, child, expand = False, fill = False, padding = 0, xalign = 0):
        """
        The pack_start() method adds child to the self.VBox, packed with reference to the start of box.
        """
        try: child.set_property( 'xalign' , xalign )
        except: pass

        self.VBox.pack_start(child, expand=expand, fill=fill, padding=padding)
        self.VBox.show_all()

    def pack_end(self, child, expand = False, fill = True, padding = 0, xalign = 0):
        """
        The pack_end() method adds child to the self.VBox, packed with reference to the end of the box
        """
        try: child.set_property( 'xalign' , xalign )
        except: pass

        self.VBox.pack_start(child, expand=expand, fill=fill, padding=padding)
        self.VBox.show_all()

    def getFocus(self):
        """
        Get the focus
        """
        if self.window:
            self.window.Focus(jh.focus.GET)

    def leaveFocus(self):
        """
        Leave the focus
        """
        if self.window:
            self.window.Focus(jh.focus.LEAVE)

    def getScreenWidth(self):
        """
        Get screen width
        """
        if self.window:
            return self.ScrolledWindow.get_screen().get_width()
        else:
            return None

    def moveWindow(self, xPos, yPos):
        self.window.move( xPos, yPos )

    def resizeWindow(self, width, height):
        self.window.resize( width, height )

class keycodeWindow(embeddedWindow):
    """
    this class creates a window to enter and check a specific keycode. If the keycode is correct the callback function wil be notifyed with True. If not False.
    """
    instanceCounter = 0
    def __init__(self, keycode, callback, title='', logo = 'PLC:\python\picture\logo.gif', infoText=None, infoLogo=gtk.STOCK_DIALOG_QUESTION, screen='MachineScreen'):
        """

        Paramter
            keycode     : the correct keycode the you expect
            callback    : a callback function that will return True or False
            title       : window title
            logo        : window logo
            infoText    : optional info text
            infoLogo    : optional info logo left to th info text
            screen      : output screen. Default: 'MachineScreen'

        Example
            keycodeWindow(keycode=807667, callback=keycodeEntered, title='KEYCODE', infoText='Please enter the PLC keycode to enter he setup.')

        """
        keycodeWindow.instanceCounter += 1
        #print 'INFO %s.%s() [%s]' %(type(self).__name__, sys._getframe().f_code.co_name, keycodeWindow.instanceCounter)
        self.keycode = keycode
        self.callback = callback

        embeddedWindow.__init__(self, usage='', title=title, logo = logo, focus = True, setTransient=True, padding = 1, plcSymbol = None, notify = None, styleName = 'embeddedWindowHeader')
        self.window.window.set_decorations( gtk.gdk.DECOR_BORDER | gtk.gdk.DECOR_TITLE )
        self.window.window.set_functions( gtk.gdk.FUNC_MOVE | gtk.gdk.FUNC_RESIZE )
        self.window.set_modal(True)
        self.window.resize(200,20)

        if infoText:
            self.pack_start(info(text=infoText, stockIcon=infoLogo))

        keyEntry = gtk.Entry()
        keyEntry.set_invisible_char('*')
        keyEntry.set_visibility(False)
        keyEntry.connect("activate", self.onEntryActivate)
        self.pack_start(keyEntry)
        keyEntry.grab_focus()

    def __del__(self):
        #print 'INFO %s.%s() [%s]' %(type(self).__name__, sys._getframe().f_code.co_name, keycodeWindow.instanceCounter)
        keycodeWindow.instanceCounter -= 1

    def onEntryActivate(self, keyEntry):
        """
        """
        newKeycode = keyEntry.get_text()
        self.callback(str(newKeycode) == str(self.keycode))
        self.callback = None
        self.keycode = None
        self.firstChild = None
        self._destroyWindow()
        self.firstChild = None

class table(gtk.Table):
    """
    This class returns a simple gtk.Table.

    Parameter see gtk.Table

    """
    instanceCounter = 0
    def __init__(self,rows=1, columns=1, homogeneous=False):
        #print 'INFO %s.%s() [%s]' %(type(self).__name__, sys._getframe().f_code.co_name, table.instanceCounter)
        table.instanceCounter += 1
        gtk.Table.__init__(self, rows=rows, columns=columns, homogeneous=homogeneous)

    def __del__(self):
        """ destructor """
        #print 'INFO %s.%s() [%s]' %(type(self).__name__, sys._getframe().f_code.co_name, table.instanceCounter)
        table.instanceCounter -= 1

    def attachToCell (self, child, col, row, xoptions = gtk.FILL, yoptions = gtk.SHRINK, xpadding = 0, ypadding = 0, xalign = 0):
        """
        Attach the child into a specified cell
        """
        try: child.set_property( 'xalign' , xalign )
        except: pass

        left_attach    = col
        right_attach   = col + 1
        top_attach     = row
        bottom_attach  = row + 1
        self.attach(child, left_attach, right_attach, top_attach, bottom_attach, xoptions=xoptions, yoptions=yoptions, xpadding=xpadding, ypadding=ypadding)

        self.show_all( )

class info(gtk.HBox):
    """
    This class returns a gtk.HBox with a stockIcon and a text to show any information.
    The background and text color are specified by the styleName.

    Parameter
        text                  : string to display
        stockIcon             : a gtk stock icon (gtk.STOCK_INFO, gtk.STOCK_DIALOG_WARNING, gtk.STOCK_HELP)
        text_border_width     : The amount of blank space to leave outside the text.
    """
    instanceCounter = 0
    def __init__(self, text, stockIcon = gtk.STOCK_DIALOG_INFO, text_border_width=10, styleName = 'info'):
        info.instanceCounter += 1
        #print 'INFO %s.%s() [%s]' %(type(self).__name__, sys._getframe().f_code.co_name, info.instanceCounter)

        gtk.HBox.__init__(self, homogeneous=False, spacing=0)
        self.set_name(styleName)

        if stockIcon:
            iconEventBox = gtk.EventBox()
            if styleName:
                iconEventBox.set_name(styleName)

            infoImage = gtk.Image()
            infoImage.set_alignment(0.0, 0.0)
            infoImage.set_padding(xpad = 5, ypad = 5)
            infoImage.set_from_stock(stockIcon, gtk.ICON_SIZE_LARGE_TOOLBAR)
            iconEventBox.add(infoImage)
            self.pack_start(iconEventBox, expand = False, fill = False, padding = 0)

        self.text = text
        self.infoTextView = gtk.TextView()
        #self.infoTextView.set_left_margin(left_margin)
        self.infoTextView.set_border_width(text_border_width)
        self.infoTextView.set_wrap_mode( gtk.WRAP_WORD )
        self.pack_start(self.infoTextView, expand = True, fill = True, padding = 0)

        self.infoTextView.unset_flags(gtk.CAN_FOCUS)

        if styleName:
            self.infoTextView.set_name(styleName)

        self.textbuffer = self.infoTextView.get_buffer()
        self.textbuffer.set_text(self.text)

    def __del__(self):
        #print 'INFO %s.%s() [%s]' %(type(self).__name__, sys._getframe().f_code.co_name, info.instanceCounter)
        info.instanceCounter -= 1


class _plcSymbol(object):
    """
    This base class is used in some plc... widgets that are using plcSymbols

    """
    plcSymbol = None
    plcFactor = None
    plcFormat = None
    plcAlias = None

    def _formatValue(self, value):
        """
        format the value to the defined plcAlias, plcFactor and plcFormat.

        Return : the formated text as string or None
        """
        #print 'INFO %s::%s plcFormat:%s plcFactor:%s)' %(__name__, sys._getframe().f_code.co_name, self.plcFormat, self.plcFactor)
        try:
            if self.plcAlias:
                newValue = self.plcAlias.get(value)
                if newValue is not None:
                    return str(newValue)

            if (type(value) is not str) and (self.plcFactor):
                value *= self.plcFactor

            if self.plcFormat is None:
                return str(value)
            else:
                return str(self.plcFormat %value)
        except Exception,msg:
            print 'EXCEPT %s::%s wrong plcFormat <%s> (msg:%s)' %(__name__, sys._getframe().f_code.co_name, self.plcFormat, msg)
            return None

    def _callback(self, value):
        """
        callback the self.notify function
        """
        if self.notify and callable(self.notify):
            self.notify( value )

    def subscribeToPlc(self, ident, downTime=0.2):
        """
        subscribe to plc symbol an connect to _onPlcSymbolChanged
        """
        self.handlePlcSymbol = jh.Subscribe(ident=ident, notify=self._onPlcSymbolChanged, downTime=downTime, onChange=True)
        if self.handlePlcSymbol is None:
            msg = 'ERROR: can not subscribe to plc symbol %s' %ident
            regHandle = MsgReg( plcTextMsgId = 'ERR_SUBSCRIBE',auxMsg=msg)
            if regHandle is not None: raiseHandle = jh.event.Raise( regHandle )

    def unSubscribeFromPlc(self):
        """
        unsubscribe from plc symbol
        """
        if self.handlePlcSymbol:
            jh.UnSubscribe( self.handlePlcSymbol )

class plcCheckButtons(gtk.Table, _plcSymbol):
    """
    This class returns a gtk.Table widget with plc check buttons.

    Parameter
        labels      : define a list of labels. the amount defines the no of checkbuttons.
        plcSymbol   : plc symbol to connect (B,W,D,)
        initValue   : initial value
        notify      : callbackfunktion that get the notification of a new value
        wrap        : wrap into the next line
        xpad        : the amount of space to add on the left and right of the widget, in pixels.
        ypad        : the amount of space to add on the top and bottom of the widget, in pixels.
        isRadio     : drow as radio button, not as check button
        styleName    : Widgets can be named, which allows you to refer to them in a GTK resource file

    Example:
        myPlcCheckButtons = plcCheckButtons( plcSymbol='DG_checkButtons' , labels=['X','Y','Z',4,5,6,7,8,9,10], notify = self.onCB )
        self.myWindow.add( myPlcCheckButtons )
    """
    instanceCounter = 0
    def __init__(self, labels, plcSymbol, initValue = None, notify = None, wrap=8, xpad = 1, ypad=0, isRadio= False, styleName = 'plcCheckButtons'):
        plcCheckButtons.instanceCounter += 1
        #print 'INFO %s.%s() <%s> [%s]' %(type(self).__name__, sys._getframe().f_code.co_name, plcSymbol, plcCheckButtons.instanceCounter)

        self.plcSymbol = plcSymbol.strip()
        self.notify = notify
        self.isRadio = isRadio
        self.oldValue = initValue

        gtk.Table.__init__(self)
        self.set_homogeneous(False)

        self.numberOfCheckButtons = len(labels)

        numberOfRows = (self.numberOfCheckButtons / wrap + 1) + 1
        numberOfLastColumns = self.numberOfCheckButtons%wrap

        self.handlePlcSymbol = None

        idx=0
        self.checkButtonDict={}
        lastButton = None
        try:
            for row in range(0,numberOfRows):
                for col in range(0,wrap):
                    vBox = gtk.VBox()

                    label = str(labels.pop(0))
                    newLabel = gtk.Label(str=label)
                    newLabel.set_padding(xpad, ypad)
                    newLabel.set_alignment(xalign=0.5, yalign=0.5)
                    if styleName:
                        newLabel.set_name(styleName)

                    if isRadio:
                        newCheckbutton = gtk.RadioButton(group = lastButton, label=None, use_underline=True)
                        lastButton = newCheckbutton
                    else:
                        newCheckbutton = gtk.CheckButton(label=None, use_underline=True)
                    newCheckbutton.connect('toggled', self.onCheckButtonToggled, idx )
                    newCheckbutton.set_alignment(xalign=0.5, yalign=0)

                    self.checkButtonDict.update({idx:newCheckbutton})
                    idx+=1


                    vBox.pack_start(child = newLabel, expand=False, fill=True, padding=1)
                    vBox.pack_start(child = newCheckbutton, expand=False, fill=True, padding=1)

                    self.attach(child = vBox, left_attach=col, right_attach=col+1, top_attach = row , bottom_attach = row+1, xoptions=gtk.FILL, yoptions=gtk.SHRINK)
                    if len(labels) == 0 :
                        # exit all loops
                        raise
        except:
            self.identPlcSymbol = GLOBAL_SYMBOL + self.plcSymbol
            self.subscribeToPlc( ident=self.identPlcSymbol )
            if initValue:
                self.putValue(initValue)

    def __del__(self):
        """ destructor """
        #print 'INFO %s.%s() <%s> [%s]' %(type(self).__name__, sys._getframe().f_code.co_name, self.plcSymbol, plcCheckButtons.instanceCounter)
        plcCheckButtons.instanceCounter -= 1

    def _onPlcSymbolChanged(self, plcValueDict, event=None):
        """
        This method runs when the plc symbol changed the value
        """
        #print 'INFO %s::%s() data:%s' %(__name__, sys._getframe().f_code.co_name, plcValueDict)

        self.plcValue = plcValueDict.values()[0]
        plcValueDec = self.plcValue

        for runIdx in range(self.numberOfCheckButtons-1,-1,-1):
            widget = self.checkButtonDict[runIdx]
            widgetState = widget.get_active()
            pot = 2**(runIdx)

            if plcValueDec / pot > 0:
                newState = True
                plcValueDec -= pot

                if self.isRadio and plcValueDec > 0:
                    print 'wrong plc value for radio type button. write old value to plc'
                    self.putValue(self.oldValue)
                    return
            else:
                newState = False

            if widgetState != newState:
                widget.set_active(newState)

    def onCheckButtonToggled(self, widget, idx ):
        """
        This method runs when any checkbutton toggled
        """
        #print 'INFO %s::%s() %s IDX:%s' %(__name__, sys._getframe().f_code.co_name, widget, idx)

        if self.handlePlcSymbol == None:
            return

        checkAxisName = widget.name
        if widget.get_active(): idxValue = '1'
        else: idxValue = '0'

        if self.isRadio:
            plcValueReturnDec = 2**idx
        else:
           plcValueDec = self.plcValue
           binStr = ''
           for runIdx in range(self.numberOfCheckButtons, -1, -1):
               pot = 2**runIdx
               if runIdx == idx:
                   binStr += idxValue
                   if plcValueDec / pot > 0:
                       plcValueDec -= pot
                   continue

               if plcValueDec / pot > 0:
                   plcValueDec -= pot
                   binStr += '1'
               else:
                   binStr += '0'
           plcValueReturnDec = int(binStr,2)
        self.putValue(plcValueReturnDec)


    def putValue(self, value):
        """
        Write the value to the PLC symbol
        """
        ret = jh.Put({self.identPlcSymbol : value})
        if ret != 1:
            #print 'ERROR %s::%s()jh.Put ret:%s, No:%s Str:%s ' %(__name__, sys._getframe().f_code.co_name, ret , jh.Errno(),jh.Errstr() )
            print 'ERROR %s::%s()jh.Put {%s:%s} /n    ret:%s, No:%s Str:%s ' %(__name__, sys._getframe().f_code.co_name, self.identPlcSymbol,  value, ret , jh.Errno(),jh.Errstr() )
            return

        self.oldValue = value

        if self.notify and callable(self.notify):
            self.notify( value )

class plcRadioButtons(plcCheckButtons):
    """
    This class returns a gtk.Table widget with plc check buttons.

    Parameter
        labels      : define a list of labels. the amount defines the no of radiobuttons.
        plcSymbol   : plc symbol to connect (B,W,D,)
        initValue   : initial value
        notify      : callbackfunktion that get the notification of a new value
        wrap        : wrap into the next line
        xpad        : the amount of space to add on the left and right of the widget, in pixels.
        ypad        : the amount of space to add on the top and bottom of the widget, in pixels.
        styleName    : Widgets can be named, which allows you to refer to them in a GTK resource file

    Example:
        myPlcradiobuttons = plcradiobuttons( plcSymbol='DG_radiobuttons' , labels=['X','Y','Z',4,5,6,7,8,9,10], notify = self.onCB )
        self.myWindow.add( myPlcradiobuttons )
    """
    instanceCounter = 0
    def __init__(self, labels, plcSymbol, initValue = None, notify = None, wrap=8, xpad = 1, ypad=0, styleName = 'plcradiobuttons'):
        #print 'INFO %s.%s() <%s> [%s]' %(type(self).__name__, sys._getframe().f_code.co_name, plcSymbol, plcRadioButtons.instanceCounter)
        plcRadioButtons.instanceCounter += 1
        plcCheckButtons.__init__(self, labels=labels, plcSymbol=plcSymbol, initValue=initValue, notify=notify, wrap=wrap, xpad=xpad, ypad=ypad, isRadio=True, styleName=styleName )

    def __del__(self):
        #print 'INFO %s.%s() <%s> [%s]' %(type(self).__name__, sys._getframe().f_code.co_name, self.plcSymbol, plcRadioButtons.instanceCounter)
        plcRadioButtons.instanceCounter -= 1

class plcCheckButton(gtk.CheckButton, _plcSymbol):
    """
    This class returns a widget with plc check buttons.

    Parameter
        plcSymbol   : plc symbol to connect (M)
        label       : define a label
        initValue   : initial value
        notify      : callbackfunktion that get the notification of a new value
        sensetive   : If sensitive is True the widget will be sensitive and the user can interact with it
        styleName   : Widgets can be named, which allows you to refer to them in a GTK resource file
    """
    instanceCounter = 0
    def __init__(self, plcSymbol, label = None, initValue = None, notify = None, sensetive = True, styleName = 'plcCheckButton'):
        plcCheckButton.instanceCounter += 1
        #print 'INFO %s.%s() <%s> [%s]' %(type(self).__name__, sys._getframe().f_code.co_name, plcSymbol, plcCheckButton.instanceCounter)

        self.plcSymbol = plcSymbol.strip()
        self.notify = notify

        gtk.CheckButton.__init__(self,label=label)

        self.set_alignment(0.0,0.0)
        self.set_sensitive(sensetive)
        if styleName:
            self.set_name(styleName)
        self.identPlcSymbol = GLOBAL_SYMBOL + self.plcSymbol
        self.subscribeToPlc( ident=self.identPlcSymbol )

        self.connect('toggled', self.onCheckButtonToggled )

        if initValue:
            self.set_active(initValue)
        self.toggled()

    def __del__(self):
        """ destructor """
        #print 'INFO %s.%s() <%s> [%s]' %(type(self).__name__, sys._getframe().f_code.co_name, self.plcSymbol, plcCheckButton.instanceCounter)
        plcCheckButton.instanceCounter -= 1

    def _onPlcSymbolChanged(self, plcValueDict, event=None):
        """
        This method runs when the plc symbol changed the value
        """
        #print 'INFO %s::%s() data:%s' %(__name__, sys._getframe().f_code.co_name, plcValueDict)
        newState = plcValueDict.values()[0]
        widgetState = self.get_active()
        if widgetState != newState:
            self.set_active(newState)

    def onCheckButtonToggled(self, widget ):
        """
        This mehtode runs when any checkbutton toggled
        """
        #print 'INFO %s::%s() %s ' %(__name__, sys._getframe().f_code.co_name, widget)

        if self.handlePlcSymbol == None:
            return

        if widget.get_active():
            value = True
        else:
            value = False

        ret = jh.Put({self.identPlcSymbol : value })
        if ret != 1:
            print 'ERROR %s::%s()jh.Put {%s:%s} /n    ret:%s, No:%s Str:%s ' %(__name__, sys._getframe().f_code.co_name, self.identPlcSymbol,  value, ret , jh.Errno(),jh.Errstr() )

        if self.notify and callable(self.notify):
            self.notify( value )


class plcEntry(gtk.Entry, _plcSymbol):
    """
    This class returns a plc gtk.Entry.

    Parameter
        plcSymbol   : plc symbol to connect (S, B, W , D)
        initValue   : initial value
        plcFactor   : factor for plcSymbol (if plcSymbol is B, W or D)
        plcFormat   : None, %4.4F, %+F %X (http://docs.python.org/2/library/stdtypes.html#string-formatting)
        plcAlias    : a dict with a translation of a plc value into a readable text. if plcAlias is defined the entry is not editable
        notify      : callback function that get the notification of a new value
        minValue    : minimum value in the mask
        maxValue    : maximum value in the mask
        maxLength   : the maximum length of the entry, or 0 for no maximum.
        width       : the width the widget should request, or -1 to unset
        height      : the height the widget should request, or -1 to unset
        editable    : True or False, on False it can not get the focus. if plcAlias is defined the entry is not editable
        sensitive   : True or False
        textColor   : text color, red black blue ...
        baseColor   : base/background color, red black blue ...
        styleName   : Widgets can be named, which allows you to refer to them in a GTK resource file
    """
    instanceCounter = 0
    def __init__(self, plcSymbol, initValue = '', plcFactor=None, plcFormat=None, plcAlias = None, notify = None, minValue = None, maxValue = None, maxLength = 0, width = -1, height = -1, editable = True, sensitive=True, textColor = None, baseColor = None, styleName = 'plcEntry' ):
        plcEntry.instanceCounter += 1
        #print 'INFO %s.%s() <%s> [%s]' %(type(self).__name__, sys._getframe().f_code.co_name, plcSymbol, plcEntry.instanceCounter)
        self.plcSymbol  = plcSymbol.strip()
        self.plcFactor  = plcFactor
        self.plcFormat  = plcFormat
        self.plcAlias   = plcAlias
        self.minValue   = minValue
        self.maxValue   = maxValue
        self.notify     = notify
        self.oldText    = ''

        if self.plcAlias:
            editable = False

        gtk.Entry.__init__(self, maxLength)
        self.set_editable(editable)
        if editable is False:
            self.unset_flags(gtk.CAN_FOCUS)
        self.set_sensitive(sensitive)
        self.set_size_request(width=width, height=height)

        if styleName:
            self.set_name(styleName)

        if baseColor:
            self.modify_base(state = gtk.STATE_NORMAL, color = gtk.gdk.color_parse(baseColor))

        if textColor:
            self.modify_text(state = gtk.STATE_NORMAL, color = gtk.gdk.color_parse(textColor))

        if '\\' in self.plcSymbol:
            self.identPlcSymbol=self.plcSymbol
        else:
            self.identPlcSymbol = GLOBAL_SYMBOL + self.plcSymbol
        self.subscribeToPlc( ident=self.identPlcSymbol )

        self.connect('activate', self.onEntryActivate )
        self.connect('changed', self.onChanged)

        if len(initValue) > 0:
            self.set_text(initValue)

        self.activate()

    def __del__(self):
        """ destructor """
        #print 'INFO %s.%s() <%s> [%s]' %(type(self).__name__, sys._getframe().f_code.co_name, self.plcSymbol, plcEntry.instanceCounter)
        plcEntry.instanceCounter -= 1

    def onChanged(self, *args):
        """
        this value runs when the value has chanced.
        if the entry is digit, except only digits.
        """
        if self.plcFactor and self.plcAlias is None:
            text = self.get_text().strip()
            text = ''.join([i for i in text if i in '0123456789.-+'])
            if (type(text) is not str):
                text = self._formatValue(text)
            self.set_text(text)

    def onEntryActivate(self, widget, event=None):
        """
        this method runs when the operator activate the entry
        """
        #print 'INFO %s::%s() ' %(__name__, sys._getframe().f_code.co_name)

        if self.plcAlias:
            return

        newValue = self.get_text()

        try:
            if self.plcFactor:
                newValue = float(newValue)
                if self.minValue and newValue < self.minValue:
                    raise Exception, 'self.minValue and newValue < self.minValue'
                if self.maxValue and newValue > self.maxValue:
                    raise Exception, 'self.maxValue and newValue > self.maxValue'
                newValue = int(round(newValue / self.plcFactor))

        except Exception, msg:
            print 'EXCEPT %s::%s wrong plcFactor <%s> (msg:%s)' %(__name__, sys._getframe().f_code.co_name, self.plcFactor, msg)
            self.set_text(self.oldText)
            return

        ret = jh.Put({self.identPlcSymbol : newValue})
        if ret != 1:
            print 'ERROR %s::%s()jh.Put {%s:%s} /n    ret:%s, No:%s Str:%s.  B W D needs plcFactor!' %(__name__, sys._getframe().f_code.co_name, self.identPlcSymbol,  newValue, ret , jh.Errno(),jh.Errstr() )
            self.set_text(self.oldText)

        self._callback(newValue)

    def _onPlcSymbolChanged(self, plcValueDict, event=None):
        """
        this method runs when the plc symbol changed the value
        """
        #print 'INFO %s::%s() data:%s' %(__name__, sys._getframe().f_code.co_name, plcValueDict)
        newValue = plcValueDict.values()[0]
        newText = self._formatValue(newValue)
        oldText = self.get_text()

        if  newText != oldText:
            self.oldText = newText
            self.set_text(newText)


class plcLabel(gtk.Label, _plcSymbol):
    """
    This class returns a plc gtk.Label.

    Parameter
        plcSymbol   : plc symbol to connect (M, B, W, D, S )
        initValue   : initial value
        plcFactor   : factor for plcSymbol, for B,W,D it must be defined
        plcFormat   : None, %4.4F, %+F %X (http://docs.python.org/2/library/stdtypes.html#string-formatting)
        plcAlias    : a dict with a translation of a plc value into a readable text
        notify      : callback function that get the notification of a new value
        preText     : text displayed before the value
        postText    : text displayed after the value
        textColor   : text color red black blue ...
        styleName   : Widgets can be named, which allows you to refer to them in a GTK resource file
    """
    instanceCounter = 0
    def __init__(self, plcSymbol = None, initValue = '', plcFactor = None, plcFormat = None, plcAlias = None,  notify = None, preText = '', postText = '', textColor = None, styleName = 'plcLabel'):
        plcLabel.instanceCounter += 1
        #print 'INFO %s.%s() <%s> [%s]' %(type(self).__name__, sys._getframe().f_code.co_name, plcSymbol, plcLabel.instanceCounter)
        self.plcSymbol  = plcSymbol
        self.plcFactor  = plcFactor
        self.plcFormat  = plcFormat
        self.plcAlias   = plcAlias
        self.notify     = notify
        self.preText    = preText
        self.postText   = postText
        self.valueLength= 1

        gtk.Label.__init__(self)
        self.setText(initValue)

        self.set_alignment(0.0, 0.0)
        self.set_padding(xpad = 0, ypad = 0)

        if styleName:
            self.set_name(styleName)

        if textColor:
            self.modify_fg(state = gtk.STATE_NORMAL, color = gtk.gdk.color_parse(textColor))

        if self.plcSymbol:
            self.identPlcSymbol = GLOBAL_SYMBOL + self.plcSymbol.strip()
            self.subscribeToPlc( ident=self.identPlcSymbol )

    def __del__(self):
        """ destructor """
        #print 'INFO %s.%s() <%s> [%s]' %(type(self).__name__, sys._getframe().f_code.co_name, self.plcSymbol, plcLabel.instanceCounter)
        plcLabel.instanceCounter -= 1

    def _onPlcSymbolChanged(self, plcValueDict, event=None):
        """
        This method runs when the plc symbol changed the value
        """
        #print 'INFO %s::%s() data:%s' %(__name__, sys._getframe().f_code.co_name, plcValueDict)
        newValue = plcValueDict.values()[0]
        newText = self._formatValue(newValue)
        self.setText(newText)

        self._callback(newValue)

    def setText(self, text):
        """
        Format the preText, text and postText. Set the result into the gtk.Label.

        Parameter
            text : text or value that should be embedded between pre and post text
        """
        self.set_text('%s%s%s' %(self.preText, text,self.postText))

class plcLevelBar(gtk.ProgressBar, _plcSymbol):
    """
    This class returns a plc gtk.ProgressBar as plc level bar.

    Parameter
        plcSymbol   : plc symbol to connect
        maxValue    : maximum value
        initValue   : initial value
        plcFactor   : factor for plcSymbol, for B,W,D it must be defined
        plcFormat   : None, %4.4F, %+d
        notify      : callback function that get the notification of a new value
        orientation : switches the orientation, (GTK ProgressBar Orientation Constants)
        width       : the width the widget should request, or -1 to unset
        height      : the height the widget should request, or -1 to unset
        barColors   : Dict with values and colors definitions {70:'green',100:'yellow',150:'red'}
        textColor   : text color red black blue ...
        preText     : text displayed before the value
        postText    : text displayed after the value
        styleName   : Widgets can be named, which allows you to refer to them in a GTK resource file
    """
    instanceCounter = 0
    def __init__(self, plcSymbol, maxValue, initValue = None, plcFactor = 1, plcFormat='%3.0F', notify = None, orientation = gtk.PROGRESS_LEFT_TO_RIGHT, width = -1, height = -1, barColors = None, textColor = None, showText = True,  preText = '', postText = '', styleName = 'plcLevelBar'):
        plcLevelBar.instanceCounter += 1
        #print 'INFO %s.%s() <%s> [%s]' %(type(self).__name__, sys._getframe().f_code.co_name, plcSymbol, plcLevelBar.instanceCounter)
        self.plcSymbol  = plcSymbol.strip()
        self.maxValue   = maxValue
        self.plcFactor  = plcFactor
        self.plcFormat  = plcFormat
        self.notify     = notify
        self.barColors  = barColors
        self.textColor  = textColor
        self.showText   = showText
        self.preText    = preText
        self.postText   = postText

        gtk.ProgressBar.__init__(self)
        self.set_orientation(orientation)
        self.set_size_request(width=width, height=height)

        if styleName:
            self.set_name(styleName)

        if self.textColor:
            self.modify_fg(state = gtk.STATE_NORMAL, color = gtk.gdk.color_parse(self.textColor))    # Text

        #self.modify_bg(state = gtk.STATE_NORMAL, color = gtk.gdk.color_parse('black'))   # Background
        #self.modify_bg(state = gtk.STATE_PRELIGHT, color = gtk.gdk.color_parse('green')) # bar

        if initValue:
            self.setLevel(initValue)

        self.identPlcSymbol = GLOBAL_SYMBOL + self.plcSymbol
        self.subscribeToPlc( ident=self.identPlcSymbol )

    def __del__(self):
        """ destructor """
        #print 'INFO %s.%s() <%s> [%s]' %(type(self).__name__, sys._getframe().f_code.co_name, self.plcSymbol, plcLevelBar.instanceCounter)
        plcLevelBar.instanceCounter -= 1

    def _onPlcSymbolChanged(self, plcValueDict, event=None):
        """
        This method runs when the plc symbol changed the value
        """
        #print 'INFO %s::%s() data:%s' %(__name__, sys._getframe().f_code.co_name, plcValueDict)
        newValue = plcValueDict.values()[0]
        self.setLevel(newValue)

        self._callback(newValue)

    def setLevel(self, newValue):
        """
        Set the level (fraction) of the bar
        """
        #print 'INFO %s::%s() value:%s' %(__name__, sys._getframe().f_code.co_name, newValue)

        newValueWithFactor = newValue * self.plcFactor

        # set Text
        if self.showText == True:
            newText = self._formatValue(newValue)
            newText = '%s%s%s' %(self.preText, newText, self.postText)
            self.set_text(newText)

        # set color
        if self.barColors:
            keys = self.barColors.keys()
            #keys.sort(reverse = True)
            keys.sort()
            keys.reverse()
            for key in keys:
                if newValueWithFactor < key:
                    color =  self.barColors[key]
                    self.modify_bg(state = gtk.STATE_PRELIGHT, color = gtk.gdk.color_parse(color))
                    #NC-Kern
                    self.modify_bg(state = gtk.STATE_SELECTED, color = gtk.gdk.color_parse(color))

        # set fraction					
        if newValueWithFactor > 0:
            fraction = 1.0 / self.maxValue * newValueWithFactor
        else:
            fraction=0
        self.set_fraction(fraction)


class plcImage(gtk.Image, _plcSymbol):
    """
    This class returns a plc gtk.Image.

    Parameter
        plcSymbol   : plc symbol to connect (M, B, W, D)
        notify      : callback function that get the notification of a new value
        imageTrue   : image (*.bmp *.jpg *.gif, ...) that will show on True
        imageFalse  : image (*.bmp *.jpg *.gif, ...) that will show on False
        imageDict   : dict with value -> image reference if plcSymbol is not marker {-1:None,0:'PLC:\python\picture\doorClose.bmp',1:'PLC:\python\picture\doorOpen.bmp',2:'PLC:\python\picture\doorError.bmp'}
    """
    instanceCounter = 0
    def __init__(self, plcSymbol, notify = None, imageTrue = gtk.STOCK_YES, imageFalse = gtk.STOCK_NO, imageDict=None):
        plcImage.instanceCounter += 1
        #print 'INFO %s.%s() <%s> [%s]' %(type(self).__name__, sys._getframe().f_code.co_name, plcSymbol, plcImage.instanceCounter)
        self.plcSymbol  = plcSymbol.strip()
        self.notify     = notify

        self.imageData  = {}

        self.TYPE       = 'type'
        self.TYPE_STOCK_ICON = 'STOCK_ICON'
        self.TYPE_FILE  = 'FILE'
        self.FILE       = 'file'

        gtk.Image.__init__(self)

        self.set_padding(xpad = 0, ypad = 0)

        # collect image data in the self.imageData. ?type ?fileType GTK / FIlE
        if imageDict:
            for imagePlcValue in imageDict:
                imageFile = imageDict[imagePlcValue]
                if imageFile[:4].upper() == 'GTK-':
                    self.imageData.update({imagePlcValue: {self.TYPE:self.TYPE_STOCK_ICON, self.FILE:imageFile} })
                elif imageFile[-4:].upper() in ('.BMP','.PNG','.GIF','.JPG'):
                    if imageFile[:4] in JH_RES_PATH_TOKEN :
                        imageFile = jh.ResPath(imageFile)
                    self.imageData.update({imagePlcValue: {self.TYPE:self.TYPE_FILE, self.FILE:imageFile}  })
        else:
            if imageTrue[:4].upper() == 'GTK-':
                self.imageData.update({1: {self.TYPE:self.TYPE_STOCK_ICON, self.FILE:imageTrue}  })
            elif imageTrue[-4:].upper() in ('.BMP','.PNG','.GIF','.JPG'):
                if imageTrue[:4] in JH_RES_PATH_TOKEN:
                    imageTrue = jh.ResPath(imageTrue)
                self.imageData.update({1: {self.TYPE:self.TYPE_FILE, self.FILE:imageTrue}  })

            if imageFalse[:4].upper() == 'GTK-':
                self.imageData.update({0: {self.TYPE:self.TYPE_STOCK_ICON, self.FILE:imageFalse} })
            elif imageFalse[-4:].upper() in ('.BMP','.PNG','.GIF','.JPG'):
                if imageFalse[:4] in JH_RES_PATH_TOKEN:
                    imageFalse = jh.ResPath(imageFalse)
                self.imageData.update({0: {self.TYPE:self.TYPE_FILE, self.FILE:imageFalse}  })

        self.identPlcSymbol = GLOBAL_SYMBOL + self.plcSymbol
        self.subscribeToPlc( ident=self.identPlcSymbol )

    def __del__(self):
        """ destructor """
        #print 'INFO %s.%s() <%s> [%s]' %(type(self).__name__, sys._getframe().f_code.co_name, self.plcSymbol, plcImage.instanceCounter)
        plcImage.instanceCounter -= 1

    def _onPlcSymbolChanged(self, plcValueDict, event=None):
        """
        this method runs when the plc symbol changed the value
        """
        #print 'INFO %s::%s() data:%s' %(__name__, sys._getframe().f_code.co_name, plcValueDict)
        newState = plcValueDict.values()[0]
        imageData = self.imageData.get(newState)
        if imageData:
            imageType = imageData.get(self.TYPE)
            imageFile = imageData.get(self.FILE)

            if imageType is self.TYPE_STOCK_ICON:
                self.set_from_stock(imageFile, gtk.ICON_SIZE_SMALL_TOOLBAR )
            elif imageType is self.TYPE_FILE:
                self.set_from_file(filename=imageFile)
            self.show_all( )

        self._callback(newState)

class plcImageWithLabel(gtk.Table):
    """
    This class returns a plc gtk.Image with label inside a table.

    Parameter
        plcSymbol   : plc symbol to connect (M)
        notify      : callback function that get the notification of a new value
        label       : define a label
        labelPos    : label position : LEFT, RIGHT, TOP, BOTTOM
        imageTrue   : image (*.bmp *.jpg *.gif, ...) that will show on True
        imageFalse  : image (*.bmp *.jpg *.gif, ...) that will show on False
        styleName   : Widgets can be named, which allows you to refer to them in a GTK resource file
    """
    instanceCounter = 0
    def __init__(self, plcSymbol, notify = None, label = None, labelPos = 'LEFT', imageTrue = gtk.STOCK_YES, imageFalse = gtk.STOCK_NO, imageDict=None, styleName = 'plcImageWithLabel'):
        plcImageWithLabel.instanceCounter += 1
        #print 'INFO %s.%s() <%s> [%s]' %(type(self).__name__, sys._getframe().f_code.co_name, plcSymbol, plcImageWithLabel.instanceCounter)
        self.plcSymbol  = plcSymbol.strip()
        self.imageTrue  = imageTrue
        self.imageFalse = imageFalse

        gtk.Table.__init__(self, rows=3, columns=3, homogeneous=False)
        if label:
            label = gtk.Label(label)

            if styleName:
                self.set_name(styleName)

            label.set_alignment(0,0)
            label.set_padding(xpad= 0, ypad= 0)
            labelPos = labelPos.upper()
            if labelPos=='LEFT':
                col = 1
                row = 2
            elif labelPos=='RIGHT':
                col = 3
                row = 2
            elif labelPos=='TOP':
                col = 2
                row = 1
            elif labelPos=='BOTTOM':
                col = 2
                row = 3
            else:
                col = 1
                row = 2
            self.attach(child=label, left_attach=col, right_attach=col+1, top_attach=row, bottom_attach=row+1,  xoptions=gtk.SHRINK, yoptions=gtk.SHRINK, xpadding=0, ypadding=0)

        self.image = plcImage( plcSymbol = plcSymbol, notify = notify, imageTrue = imageTrue, imageFalse = imageFalse, imageDict = imageDict )
        #self.image = gtk.Image()
        self.attach(child=self.image, left_attach=2, right_attach=3, top_attach=2, bottom_attach=3,  xoptions=gtk.SHRINK, yoptions=gtk.SHRINK, xpadding=0, ypadding=0)

    def __del__(self):
        """ destructor """
        #print 'INFO %s.%s() <%s> [%s]' %(type(self).__name__, sys._getframe().f_code.co_name, self.plcSymbol, plcImageWithLabel.instanceCounter)
        plcImageWithLabel.instanceCounter -= 1

class plcLineGraph(gtk.DrawingArea):
    """
    This class returns a drawing area tha contains line graphs.

    Parameter
        plcSymbol *1      : plc symbol to connect to the graph (B, W , D)

        minValue          : minimum value of the graph
        maxValue,         : maximum value of the graph
        listLength        : number of values in the list
        scanTime          : time after reading the plcSymbol and redraw the graph
        width             : width of the widget in pixel
        height            : hight of the widget in pixel
        lineWidth         : line width of the graph(s) in pixel
        helpLines         : tupel  with a tuple for x and y help line.
                            syntax : ((x1,x2,...),(y1,y2,...))
                            x is a value in the range of min- maxValue.
                            y is a value in the range from 0 to (listLength*scanTime) in secounds.
                            Exapmple ((10,15,20),(-50,0,50,100))
        plcSymbolStart    : None, or a plc symbol that starts the trace on True und will stop the trace on False
        fileNameToSave    : None, or a a file name to save the values into
        styleName         : Widgets can be named, which allows you to refer to them in a GTK resource file

        plcFactor *1      : factor for plcSymbol
        plcFormat *1      : None, %4.4F, %+d
        notify    *1      : callback function that get the notification of a new value
        color     *1      : color the graph for the defined plcSymbol
        showText  *1      : show the legend text with preText value und postText if defined
        preText   *1      : text displayed before the value
        postText  *1      : text displayed after the value

          *1 this parameters will create a _graph object
    """
    instanceCounter = 0
    def __init__(self, plcSymbol, minValue, maxValue, listLength= 200 , scanTime = 500, width = 400, height = 200, lineWidth = 2, helpLines = None, plcSymbolStart = None, save=False, styleName = 'plcLineGraph', plcFactor = 1, plcFormat = '%3.0F', notify = None, color = 'blue', showText = True,  preText = '', postText = ''):
        plcLineGraph.instanceCounter += 1
        #print 'INFO %s.%s() <%s> [%s]' %(type(self).__name__, sys._getframe().f_code.co_name, plcSymbol, plcLineGraph.instanceCounter)
        self.plcSymbol      = plcSymbol.strip()
        self.minValue       = minValue
        self.maxValue       = maxValue
        self.listLength     = listLength
        self.scanTime       = scanTime
        self.width          = width
        self.height         = height
        self.lineWidth      = lineWidth
        self.helpLines      = helpLines
        self.plcSymbolStart = plcSymbolStart
        self.save           = save
        self.styleName      = styleName

        self.graphList      =   []
        self.graphLegendLength = 0

        self.xFactor        = (1.0*self.width) /(self.listLength*(self.scanTime/1000.0))
        self.yFactor        = (1.0*self.height) / (self.maxValue - self.minValue)
        self.yOffset        = abs(self.minValue) * self.yFactor
        if self.minValue > 0:
            self.yOffset *= -1

        self.exposed        = False
        self.stopGraph      = False

        gtk.DrawingArea.__init__(self)

        if styleName:
            self.set_name(styleName)

        self.set_size_request(width+1, height+1)
        self.pangolayout = self.create_pango_layout("")

        self.set_events(gtk.gdk.POINTER_MOTION_MASK |
                             gtk.gdk.POINTER_MOTION_HINT_MASK )
        self.connect("expose-event", self.area_expose_cb)
        self.show()

        self.addGraph(plcSymbol, plcFactor, plcFormat, notify, color, showText, preText, postText)

        if self.plcSymbolStart == None:
            gobject.timeout_add( self.scanTime, self.getPlcData )
        else:
            self.handlePlcSymbolStart = jh.Subscribe(ident= GLOBAL_SYMBOL + self.plcSymbolStart, notify=self._onPlcSymbolStartChanged, onChange=True)
            if self.handlePlcSymbolStart is None:
                msg = 'ERROR: can not subscribe to plc symbol %s' %GLOBAL_SYMBOL + self.plcSymbolStart
                regHandle = MsgReg( plcTextMsgId = 'ERR_SUBSCRIBE',auxMsg=msg)
                if regHandle is not None: raiseHandle = jh.event.Raise( regHandle )

    def __del__(self):
        """ destructor """
        #print 'INFO %s.%s() <%s> [%s]' %(type(self).__name__, sys._getframe().f_code.co_name, self.plcSymbol, plcLineGraph.instanceCounter)
        plcLineGraph.instanceCounter -= 1

    def area_expose_cb(self, area, event):
        """
        callback function for redrawing the area on a "expose-event" event
        """
        if self.exposed == False:
            for graph in self.graphList:
                graph.values = []
                color = graph.color
                gc = self.window.new_gc()
                gc.line_width = self.lineWidth

                gc.set_foreground(gtk.gdk.color_parse(color))
                gc.set_background(gtk.gdk.color_parse(color))

                gc.set_rgb_fg_color(gtk.gdk.color_parse(color))
                gc.set_rgb_bg_color(gtk.gdk.color_parse(color))
                graph.gc  = gc

            self.gcHelpline =   self.window.new_gc()
            self.gcHelpline.set_rgb_fg_color(gtk.gdk.color_parse('grey'))
            self.gcHelpline.set_rgb_bg_color(gtk.gdk.color_parse('white'))

            self.exposed = True

        self.drawHelplines()
        self.drawGraph()

    def _onPlcSymbolStartChanged(self, plcValueDict, event=None):
        """
        this method runs when the plc symbol start changed the value.
        if it is True run the graph. if it is False stop the graph
        """
        #print 'INFO %s::%s() data:%s' %(__name__, sys._getframe().f_code.co_name, plcValueDict)
        newValue = plcValueDict.values()[0]
        if newValue == True:
            self.stopGraph = False
            for graph in self.graphList:
                graph.values = []
            self.queue_draw()
            gobject.timeout_add( self.scanTime, self.getPlcData )
        else:
            self.stopGraph = True

    def addGraph (self, plcSymbol, plcFactor = 1, plcFormat='%3.0F', notify = None, color = 'blue', showText = True,  preText = '', postText = ''):
        """
        add a new _graph object to the graphList.

        Parameter
            plcSymbol       : plc symbol to connect to the graph (B, W , D)
            plcFactor       : factor for plcSymbol
            plcFormat       : None, %4.4F, %+d

            color           : color the graph for the defined plcSymbol
            showText        : show the legend text with preText value und postText if defined
            preText         : text displayed before the value
            postText        : text displayed after the value
        """
        self.graphList.append(_graph(plcSymbol=plcSymbol, plcFactor=plcFactor, plcFormat=plcFormat, notify = notify, color=color, showText=showText,  preText=preText, postText=postText))

    def getPlcData(self):
        """
        this method will be called from gobject.timeout_add event after self.scanTime and get the plc data .
        """
        #print 'INFO %s::%s()' %(__name__, sys._getframe().f_code.co_name)

        drawQueue=False
        for graph in self.graphList:
            plcSymbol = graph.plcSymbol
            plcFactor = graph.plcFactor
            plcValueDict = jh.Get(GLOBAL_SYMBOL + plcSymbol)
            newValue = plcValueDict.values()[0]

            valuesList = graph.values

            # plcFactor
            if plcFactor and type(newValue) != str:
                newValueWithFactor = newValue * plcFactor
                valuesList.append(newValueWithFactor)
            else:
                valuesList.append(newValue)

            # reduce list length
            if len(valuesList) > self.listLength:
                #popLength = int(len(valuesList)*0.2)
                #graph.values = valuesList[popLength:]
                graph.valuesOutOfList = graph.valuesOutOfList + 1
                graph.oldValue = valuesList[0]
                graph.values.pop(0)
                drawQueue = True

            graph._callback(newValue)

        if self.exposed:
            if drawQueue:
                self.queue_draw()
            else:
                self.drawGraph()

        if self.stopGraph == False:
            return True #True : to call that function once again


    def drawHelplines(self):
        """
        draw helplines and frame into the drawing area
        """

        segments=[]
        pangolayout = self.create_pango_layout("")

        if self.helpLines:
            # X help lines
            helpLinesX = self.helpLines[0]
            for helpLineX in helpLinesX:
                hlx = int( helpLineX * self.xFactor)
                segments.append((hlx, 0, hlx, self.height))
                pangolayout.set_text('%s' %helpLineX)
                pangolayoutSizeX, pangolayoutSizeY = pangolayout.get_pixel_size()
                self.window.draw_layout(self.gcHelpline, hlx, self.height-pangolayoutSizeY, pangolayout,  foreground=gtk.gdk.color_parse('black'))

            self.window.draw_segments(self.gcHelpline, tuple(segments))

            # y help lines
            segments=[]
            helpLinesY = self.helpLines[1]
            for helpLineY in helpLinesY:
                hly = int(self.height - (helpLineY * self.yFactor) - self.yOffset )
                segments.append((0, hly, self.width, hly))
                yHelpLineText = '%s' %helpLineY
                yHelpLineText = yHelpLineText.rjust(5)
                pangolayout.set_text(yHelpLineText)
                pangolayoutSizeX, pangolayoutSizeY = pangolayout.get_pixel_size()
                self.window.draw_layout(self.gcHelpline, self.width-pangolayoutSizeX, hly-pangolayoutSizeY, pangolayout,  foreground=gtk.gdk.color_parse('black'))

            self.window.draw_segments(self.gcHelpline, tuple(segments))

        # frame
        segments=[]
        segments=(
                  (0, 0, self.width, 0),
                  (self.width, 0, self.width, self.height),
                  (self.width, self.height, 0, self.height),
                  (0, self.height, 0, 0),
                  )
        self.window.draw_segments(self.gcHelpline, tuple(segments))

        pangolayout.set_text('t[s]')
        pangolayoutSizeX, pangolayoutSizeY = pangolayout.get_pixel_size()
        self.window.draw_layout(self.gcHelpline, self.width-pangolayoutSizeX, self.height-pangolayoutSizeY, pangolayout,  foreground=gtk.gdk.color_parse('black'))


    def drawGraph(self):
        """
        draw the graph into the drawing area

        Parameter
            unused
        """
        #print 'INFO %s::%s() value:%s' %(__name__, sys._getframe().f_code.co_name, self.plcSymbol)
        if self.window is None:
            return

        xTextPosition=2
        yTextPosition=2

        for graph in self.graphList:

            values      = graph.values
            gc          = graph.gc

            x=0
            points=[]
            value=''
            for value in values:
                xPoint = int(x * (self.xFactor*self.scanTime/1000.0) )
                yPoint = int(self.height - (value * self.yFactor) - self.yOffset )
                points.append((xPoint,yPoint))
                x+=1

            if len(points) != 0:
                self.window.draw_lines(gc, points)

            if graph.showText is True:
                newText = graph._formatValue(value / graph.plcFactor)
                legendText = "%s%s%s" %(graph.preText, newText, graph.postText)
                legendTextlength = len(legendText)

                if legendTextlength < self.graphLegendLength:
                    legendText = legendText.ljust(self.graphLegendLength)
                else:
                    self.graphLegendLength = legendTextlength

                self.pangolayout.set_text(legendText)
                self.window.draw_layout(gc, xTextPosition, yTextPosition, self.pangolayout, foreground=None, background=gtk.gdk.color_parse('white'))

                yTextPosition += 15

class _graph(_plcSymbol):
    """
    This class returns a _graph object used in the class plcLineGraph.

    Parameter
        plcSymbol       : plc symbol to connect to the graph (B, W , D)
        plcFactor       : factor for plcSymbol
        None, %4.4F, %+F %X (http://docs.python.org/2/library/stdtypes.html#string-formatting)
        color           : color the graph for the defined plcSymbol
        showText        : show the legend text with preText value und postText if defined
        preText         : text displayed before the value
        postText        : text displayed after the value
    """
    instanceCounter = 0
    def __init__(self, plcSymbol, plcFactor = 1, plcFormat=None, notify = None, color = 'blue', showText = True,  preText = '', postText = ''):
        _graph.instanceCounter += 1
        #print 'INFO %s.%s() <%s> [%s]' %(type(self).__name__, sys._getframe().f_code.co_name, plcSymbol, _graph.instanceCounter)
        self.plcSymbol  = plcSymbol.strip()
        self.values     = []
        self.plcFactor  = plcFactor
        self.plcFormat  = plcFormat
        self.notify     = notify
        self.color      = color
        self.showText   = showText
        self.preText    = preText
        self.postText   = postText
        self.maximum = 0
        self.oldAverage = 0
        self.valuesOutOfList = 0
        self.oldValue = 0

    def __del__(self):
        """ destructor """
        #print 'INFO %s.%s() <%s> [%s]' %(type(self).__name__, sys._getframe().f_code.co_name, self.plcSymbol, _graph.instanceCounter)
        _graph.instanceCounter -= 1

    def getValueMax(self):
        """
        Returns the current maximum.
        """
        maxCurrent = max(self.values)
        if self.maximum < maxCurrent:
            self.maximum = maxCurrent
        return self.maximum

    def getValueAverage(self):
        """
        Calculates average of all measured data since last reset (onResetButtonClicked), for detailed formula description look up 'weighted average' e.g. on Wikipedia
        """
        if self.valuesOutOfList > 0:
            self.oldAverage = float((self.oldValue + self.oldAverage * (self.valuesOutOfList-1))) / float(self.valuesOutOfList)
        ratio = float(self.valuesOutOfList) / float(len(self.values))
        average = float(ratio * self.oldAverage + float(sum(self.values))/float(len(self.values))) / float((ratio + 1))
        return average


class plcHelp(table, _plcSymbol):
    """
    This class returns a treeview area that contains status pixbufs and texts from the text data base.

    Parameter
        plcTxtDomain        : python plc text database domain name
        infoBoxVisible      : False, info box for additional informations visible at the buttom of the window
                              the info texts are the texts starting from the second line of the help texts
        styleName           : Widgets can be named, which allows you to refer to them in a GTK resource file

    Parameter for method append_line
        lineTxtId           : python plc text database ID for the help texts (e.g. TC_HLP_SERVICE1_101, TC_HLP_SERVICE2_101, ...)
        plcSymbolStruct     : None, plc symbol for a structure to connect to one line of the treeview
                              If the parameter is not None, the following elements are used:
                              plcSymbolStruct.HELP_LINE_SELECTED
                              plcSymbolStruct.HELP_LINE_STATUS
                              plcSymbolStruct.HELP_LINE_ENABLE
        plcSymbolSelected   : None, plc symbol to connect to the active line of the treeview
                              Is used only if the plcSymbolStruct is None
        plcSymbolStatus     : None, plc symbol to connect to the status pixbufs
                              Is used only if the plcSymbolStruct is None
        plcSymbolEnable     : None, plc symbol to connect to enable/disable a line
                              Is used only if the plcSymbolStruct is None
        plcSymbolHide       : None, plc symbol to connect to hide/show a line
                              Is used only if the plcSymbolStruct is None
    """
    instanceCounter = 0
    def __init__(self, plcTxtDomain, infoBoxVisible=False, styleName = 'info'):
        plcImage.instanceCounter += 1
        #print 'INFO %s.%s() <%s> [%s]' %(type(self).__name__, sys._getframe().f_code.co_name, plcSymbolLineNb, plcImage.instanceCounter)
        self.plcTxtDomain = plcTxtDomain.strip()
        self.lastSelection = None
        self.dictLinePlcSymbols = {}
        self.dictLineTextInformation = {}
        self.dictPlcSymbolEnableValue = {}

        self.treeIter = []

        gtk.Table.__init__(self)

        bindTextDomain(path = 'LANGUAGE', domain = self.plcTxtDomain)

        self.hasFocus = False
        self.hlpDict = {}
        self.liststore = gtk.ListStore(str, str, gobject.TYPE_BOOLEAN)

        # Creation of the filter, from the model
        self.modelfilter = self.liststore.filter_new()
        self.modelfilter.set_visible_column(2)

        self.treeview = gtk.TreeView(self.modelfilter)
        self.treeview.set_headers_visible(False)

        self.plcValueStatus = 0
        self.plcValueDisable =0

        self.renderer_pixbuf = gtk.CellRendererPixbuf()
        self.column_pixbuf = gtk.TreeViewColumn("Status", self.renderer_pixbuf, stock_id=0)
        self.treeview.append_column(self.column_pixbuf)
        self.renderer_pixbuf.set_fixed_size(width=35, height=10)

        self.renderer_text = gtk.CellRendererText()
        self.column_text = gtk.TreeViewColumn("     ", self.renderer_text, text=1)
        self.treeview.append_column(self.column_text)

        self.scrolledWindow = gtk.ScrolledWindow()
        self.scrolledWindow.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)

        self.scrolledWindow.add(self.treeview)

        self.descrLbl = info(text="\n\n",text_border_width=10)
        self.descrLbl.set_homogeneous(False)

        eventBox = gtk.EventBox()
        eventBox.add(gtk.Label(""))
        eventBox.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse('#FFFFFF'))

        self.attachToCell(eventBox, xoptions=gtk.FILL, yoptions=gtk.SHRINK,col=0,row=9)
        self.attachToCell(self.scrolledWindow, xoptions=gtk.EXPAND|gtk.FILL, yoptions=gtk.EXPAND|gtk.FILL,col=0,row=10)

        if infoBoxVisible == True:
            self.attachToCell(self.descrLbl,   xoptions=gtk.FILL, yoptions=gtk.FILL, col=0,row=11)

        self.selection = self.treeview.get_selection()
        self.selection.connect('changed', self.on_selection_changed)

        self.treeview.connect("expose-event", self._onTree_expose)
        self.treeview.connect("focus-out-event", self._onFocusOut)


    def __del__(self):
        """ destructor """
        #print 'INFO %s.%s() <%s> [%s]' %(type(self).__name__, sys._getframe().f_code.co_name, self.plcSymbolLineNb, plcImage.instanceCounter)
        plcImage.instanceCounter -= 1


    def append_line(self, lineTxtId, plcSymbolStruct=None, plcSymbolSelected=None, plcSymbolStatus=None, plcSymbolEnable=None, plcSymbolHide=None):
        """
        this method append a new line to the treeview and connect the signals to the plc
        """
        #print 'INFO %s::%s() data:%s, %s, %s, %s, %s, %s' %(__name__, sys._getframe().f_code.co_name, lineTxtId, plcSymbolStruct, plcSymbolSelected, plcSymbolStatus, plcSymbolEnable, plcSymbolHide)
        dictTextInformation = {}

        lineNumber = len(self.liststore)

        if plcSymbolStruct is not None:
            plcSymbolSelected = plcSymbolStruct + '.' + HELP_LINE_SELECTED
            plcSymbolStatus = plcSymbolStruct + '.' + HELP_LINE_STATUS
            plcSymbolEnable = plcSymbolStruct + '.' + HELP_LINE_ENABLE
            plcSymbolHide  = plcSymbolStruct + '.' + HELP_LINE_HIDE

        dictPlcSymbols = {'plcSymbolSelected':plcSymbolSelected,'plcSymbolStatus':plcSymbolStatus, 'plcSymbolEnable':plcSymbolEnable, 'plcSymbolHide':plcSymbolHide}

        self.dictLinePlcSymbols.update({lineNumber:dictPlcSymbols})

        #get texts
        plcTxt   = txt(lineTxtId)
        lineList = plcTxt.splitlines()

        dictTextInformation["MSG_ID"]=lineTxtId
        dictTextInformation["MSG"]= "#{0:02d}  ".format(lineNumber) + lineList[0]

        del lineList[0]

        MsgHlp = ""

        for elements in lineList:
            if MsgHlp != "":
                MsgHlp = MsgHlp + '\r\n'

            MsgHlp = MsgHlp + elements

        dictTextInformation["MSG_Hlp"]=MsgHlp

        self.dictLineTextInformation.update({lineNumber:dictTextInformation})

        self.liststore.append([gtk.STOCK_NO, dictTextInformation["MSG"], True])

        #get the iter
        self.treeIter = []
        iter = self.liststore.get_iter_first()

        while iter:
            self.treeIter.append(iter)
            iter = self.liststore.iter_next(iter)

        if plcSymbolEnable:
            identPlcSymbol = GLOBAL_SYMBOL + plcSymbolEnable.strip()
            self.subscribeToPlc( ident=identPlcSymbol )

        if plcSymbolStatus:
            identPlcSymbol = GLOBAL_SYMBOL + plcSymbolStatus.strip()
            self.subscribeToPlc( ident=identPlcSymbol )

        if plcSymbolHide:
            identPlcSymbol = GLOBAL_SYMBOL + plcSymbolHide.strip()
            self.subscribeToPlc( ident=identPlcSymbol )


    def on_selection_changed(self, selection, *args):
        model, iter = selection.get_selected()

        if self.lastSelection is not None:
            plcSymbolLineActive = self.dictLinePlcSymbols[self.lastSelection]['plcSymbolSelected']
            jh.Put({(GLOBAL_SYMBOL + plcSymbolLineActive) : False})
            self.lastSelection = None

        if not iter:
            return False

        i = 0
        for treeIter in self.treeIter:
            if self.liststore.get_value(treeIter,1) == model.get_value(iter,1):
               if self.liststore[treeIter][2] == True:
                   lineNumber = i

            i = i + 1

        plcSymbolLineActive = self.dictLinePlcSymbols[lineNumber]['plcSymbolSelected']
        jh.Put({(GLOBAL_SYMBOL + plcSymbolLineActive) : True})

        self.lastSelection   =  lineNumber

        try:
            self.descrLbl.textbuffer.set_text(self.dictLineTextInformation[lineNumber]['MSG_Hlp'])
        except:
            return None


    def _onFocusOut(self, tree, event):
        self.hasFocus = False


    def _onTree_expose(self, tree, event):
        if self.hasFocus == False:
            self.hasFocus = True
            tree.grab_focus()


    def _onPlcSymbolChanged(self, plcValueDict, event=None):
        """
        this method runs when the plc symbol changed the value
        """
        #print 'INFO %s::%s() data:%s' %(__name__, sys._getframe().f_code.co_name, plcValueDict)

        plcValue = plcValueDict.values()[0]

        for lineNumber, dictPlcSymbols in self.dictLinePlcSymbols.iteritems():
            for function, plcSymbol in dictPlcSymbols.iteritems():
                if function == 'plcSymbolEnable' and plcValueDict.keys()[0] == plcSymbol:
                    self.dictPlcSymbolEnableValue.update({lineNumber:plcValue})
                    self.column_text.set_cell_data_func(self.renderer_text,self._changeTxtColumn)
                elif function == 'plcSymbolStatus' and plcValueDict.keys()[0] == plcSymbol:
                    self._changePixbufColumn(self.liststore, self.treeIter, [plcValue, lineNumber])
                elif function == 'plcSymbolHide' and plcValueDict.keys()[0] == plcSymbol:
                    self._hideLine(self.liststore, self.treeIter, [plcValue, lineNumber])

        self.show_all( )

    def _hideLine(self, listStore, iterList, user_data):

        if user_data[0] == True:
           treeSelection =  self.treeview.get_selection()

           if  treeSelection.get_selected_rows()[1] <> []:
               path = str(treeSelection.get_selected_rows()[1][0])

               lineNumber = int(path.strip('(),'))

               if lineNumber == user_data[1]:
                  if len(self.treeview.get_model()) - 1 == lineNumber:
                    self.treeview.set_cursor((lineNumber-1,))
                  else:
                    self.treeview.set_cursor((lineNumber+1,))

           store_iter = iterList[user_data[1]]
           listStore[store_iter][2] = False
        else:
           store_iter = iterList[user_data[1]]
           listStore[store_iter][2] = True


    def _changeTxtColumn(self, column, cell, model, iter):
        i = 0
        for treeIter in self.treeIter:
            cell_renderer = column.get_cell_renderers()[0]

            if self.liststore.get_value(treeIter,1) == model.get_value(iter,1):
               if self.liststore[treeIter][2] == True:
                   if self.dictPlcSymbolEnableValue[i] == True:
                       cell_renderer.set_property('foreground' , "#000000")
                   else:
                       cell_renderer.set_property('foreground' , "#BFBFBF")

            i = i + 1


    def _changePixbufColumn(self, listStore, iterList, user_data):
        if user_data[0] == True:
           store_iter = iterList[user_data[1]]
           listStore[store_iter][0] = gtk.STOCK_YES
        else:
           store_iter = iterList[user_data[1]]
           listStore[store_iter][0] = gtk.STOCK_NO


class plcComboBox(gtk.ComboBox, _plcSymbol):
    """
    This class returns a plc gtk.ComboBox.

    Parameter
        plcSymbol   : plc symbol to connect (M)
        text        : list of combo box texts
        notify      : callback function that get the notification of a new value
        preText     : text displayed before the value
        postText    : text displayed after the value
        width       : width of the widget in pixel
        height      : hight of the widget in pixel
        textColors  : list of text colors for combo box texts [red, black, blue ...]
        baseColors  : list of background colors for combo box texts [red, black, blue ...]
        sensetive   : If sensitive is True the widget will be sensitive and the user can interact with it
        styleName   : Widgets can be named, which allows you to refer to them in a GTK resource file
    """
    instanceCounter = 0
    def __init__(self, textList, textColors = None, baseColors = None, plcSymbol = None, notify = None, width = -1, height = -1, sensitive=True, styleName = 'plcLabel'):
        plcLabel.instanceCounter += 1
        #print 'INFO %s.%s() <%s> [%s]' %(type(self).__name__, sys._getframe().f_code.co_name, plcSymbol, plcLabel.instanceCounter)
        self.plcSymbol   = plcSymbol
        self.textList    = textList
        self.notify      = notify
        self.width       = width
        self.height      = height
        self.textColors  = textColors
        self.baseColors  = baseColors

        self.valueLength= 1

        liststore = gtk.ListStore(str)

        gtk.ComboBox.__init__(self, liststore)

        self.cell_renderer = gtk.CellRendererText()

        self.pack_start(self.cell_renderer, True)

        self.add_attribute(self.cell_renderer, "text", 0)

        self.set_size_request(width=width, height=height)

        self.set_sensitive(sensitive)

        for element in self.textList:
            self.append_text(element)

        if styleName:
            self.set_name(styleName)

        if self.plcSymbol:
            self.identPlcSymbol = GLOBAL_SYMBOL + self.plcSymbol.strip()

            self.connect('changed', self.onComboBoxChanged)
            self.connect('popup', self.onComboBoxPopup)

            self.subscribeToPlc( ident=self.identPlcSymbol )


    def __del__(self):
        """ destructor """
        #print 'INFO %s.%s() <%s> [%s]' %(type(self).__name__, sys._getframe().f_code.co_name, self.plcSymbol, plcLabel.instanceCounter)
        plcLabel.instanceCounter -= 1


    def onComboBoxChanged(self, widget, event=None):
        """
        this method runs when the operator activate the entry
        """
        #print 'INFO %s::%s() ' %(__name__, sys._getframe().f_code.co_name)

        newValue = self.get_active()

        ret = jh.Put({self.identPlcSymbol : newValue})

        if ret != 1:
            #print 'ERROR %s::%s()jh.Put {%s:%s} /n    ret:%s, No:%s Str:%s.  B W D needs plcFactor!' %(__name__, sys._getframe().f_code.co_name, self.identPlcSymbol,  newValue, ret , jh.Errno(),jh.Errstr() )
            self.set_text(self.oldText)

        self._callback(newValue)


    def onComboBoxPopup(self, widget, event=None):
        """
        this method runs when the operator activate the entry
        """
        #print 'INFO %s::%s() ' %(__name__, sys._getframe().f_code.co_name)

        self.cell_renderer.set_property('foreground' , 'black')


    def _onPlcSymbolChanged(self, plcValueDict, event=None):
        """
        This method runs when the plc symbol changed the value
        """
        #print 'INFO %s::%s() data:%s' %(__name__, sys._getframe().f_code.co_name, plcValueDict)

        newValue = plcValueDict.values()[0]

        if len(self.textList)-1 < newValue:
            newValue = 0

        self.set_active(newValue)

        print  len(self.textColors)
        if self.textColors:
            if len(self.textColors) == 1:
                self.cell_renderer.set_property('foreground' , self.textColors[0])
            else:
                print self.textColors[newValue]
                self.cell_renderer.set_property('foreground' , self.textColors[newValue])

        if self.baseColors:
            if len(self.baseColors) == 1:
                self.modify_base(gtk.STATE_NORMAL, gtk.gdk.color_parse(self.baseColors[0]))
            else:
                self.modify_base(gtk.STATE_NORMAL, gtk.gdk.color_parse(self.baseColors[newValue]))


class plcToggleButton(gtk.ToggleButton, _plcSymbol):
    """
    This class returns a widget with plc toggle button.

    Parameter
        plcSymbol   : plc symbol to connect (M)
        label       : define a label
        initValue   : initial value
        notify      : callbackfunktion that get the notification of a new value
        sensetive   : If sensitive is True the widget will be sensitive and the user can interact with it
        styleName   : Widgets can be named, which allows you to refer to them in a GTK resource file
    """
    instanceCounter = 0
    def __init__(self, plcSymbol, label = None, initValue = None, notify = None, sensetive = True, styleName = None):
        plcCheckButton.instanceCounter += 1
        #print 'INFO %s.%s() <%s> [%s]' %(type(self).__name__, sys._getframe().f_code.co_name, plcSymbol, plcCheckButton.instanceCounter)

        self.plcSymbol = plcSymbol.strip()
        self.notify = notify

        gtk.ToggleButton.__init__(self,label=label)

        self.set_alignment(0.0,0.0)
        self.set_sensitive(sensetive)
        if styleName:
            self.set_name(styleName)
        self.identPlcSymbol = GLOBAL_SYMBOL + self.plcSymbol
        self.subscribeToPlc( ident=self.identPlcSymbol )

        self.connect('toggled', self.onCheckButtonToggled )

        if initValue:
            self.set_active(initValue)
        self.toggled()

    def __del__(self):
        """ destructor """
        #print 'INFO %s.%s() <%s> [%s]' %(type(self).__name__, sys._getframe().f_code.co_name, self.plcSymbol, plcCheckButton.instanceCounter)
        plcCheckButton.instanceCounter -= 1

    def _onPlcSymbolChanged(self, plcValueDict, event=None):
        """
        This method runs when the plc symbol changed the value
        """
        #print 'INFO %s::%s() data:%s' %(__name__, sys._getframe().f_code.co_name, plcValueDict)
        newState = plcValueDict.values()[0]
        widgetState = self.get_active()
        if widgetState != newState:
            self.set_active(newState)

    def onCheckButtonToggled(self, widget ):
        """
        This mehtode runs when any checkbutton toggled
        """
        #print 'INFO %s::%s() %s ' %(__name__, sys._getframe().f_code.co_name, widget)

        if self.handlePlcSymbol == None:
            return

        if widget.get_active():
            value = True
        else:
            value = False

        ret = jh.Put({self.identPlcSymbol : value })
        if ret != 1:
            print 'ERROR %s::%s()jh.Put {%s:%s} /n    ret:%s, No:%s Str:%s ' %(__name__, sys._getframe().f_code.co_name, self.identPlcSymbol,  value, ret , jh.Errno(),jh.Errstr() )

        if self.notify and callable(self.notify):
            self.notify( value )

class mcgSelect(gtk.ComboBox):
    """
    This class read from the mcg file the defined token and will display a selection.
    """
    INDEX_LINE, INDEX_ACTIVE, INDEX_VALUE, INDEX_COMMENT = range(4)

    def __init__(self, file, token, width = -1, height = -1, styleName = 'mcgSelect'):
        """
        Parameter
          file : path and file name to the compiler configuration
          token : compiler token
        """

        self.file = file
        self.token = token

        self.width       = width
        self.height      = height

        liststore = gtk.ListStore(str)
        gtk.ComboBox.__init__(self, liststore)
        self.cell_renderer = gtk.CellRendererText()
        self.pack_start(self.cell_renderer, True)
        self.add_attribute(self.cell_renderer, "text", 0)
        self.set_size_request(width=width, height=height)
        self.set_sensitive(True)

        self.tokenDataList = [] # [[line, active, value, comment]]
        self.oldSelectionIndex = None

        mcgFile = open(self.file,'r')
        mcgData = mcgFile.read()
        mcgFile.close()

        it = re.finditer(r"([;|*])? *DEFINE *%s *= *\"(.*)\" *;?(.*)" %token, mcgData, re.I)
        # ([;|*])?    ; or * or nothing / Group activeLine
        #  *         whitespaces allowed
        # DEFINE     DEFINE must be in the line
        #  *         whitespaces allowed
        # %s         the token for the cfgDefinition
        #  *         whitespaces allowed
        # =          = must be in the line
        #  *         whitespaces allowed
        # \"         " is the start of the value
        # (.*)       Group cfgValue
        # \"         " is the end of the value
        #  *         whitespaces allowed
        # (;.*)      Group cfgComment

        for m in it:
            line = m.group(0)
            line.lstrip('*')
            line.lstrip(';')
            activeLine = not bool(m.group(1))
            cfgValue = m.group(2)
            cfgComment = m.group(3)
            self.tokenDataList.append([line, activeLine, cfgValue, cfgComment])

        for valueData in self.tokenDataList:
            text = '%-24s %s' %(valueData[self.INDEX_VALUE], valueData[self.INDEX_COMMENT])
            self.append_text(text)
            if valueData[self.INDEX_ACTIVE]:
                self.oldSelectionIndex = self.tokenDataList.index(valueData)
                self.set_active(self.oldSelectionIndex)
                self.activeLine = valueData[self.INDEX_LINE]

        if styleName:
            self.set_name(styleName)
        self.connect('changed', self.onComboBoxChanged)


    def onComboBoxChanged(self, widget, event=None):
        """
        this method runs when the operator activate the comboBox
        """
        print 'INFO %s::%s() ' %(__name__, sys._getframe().f_code.co_name)

        oldValueData = self.tokenDataList[self.oldSelectionIndex]
        oldLine = oldValueData[self.INDEX_LINE]
        #oldModifityLine = '*%s' %oldLine

        newSelectionIndex = self.get_active()
        newValueData = self.tokenDataList[newSelectionIndex]
        newLine = newValueData[self.INDEX_LINE]

        self.oldSelectionIndex = newSelectionIndex

        fileNameTmp = self.file+'.tmp'
        oldFile = open(self.file,'r')
        newFile = open(fileNameTmp,'w')
        try:
            for line in oldFile:
                #print line
                #stripedLine = line.strip()

                if oldLine[1:] in line:
                    writeLine = '%s\n' %oldLine
                    if not (writeLine[0] in (';','*')):
                        writeLine = ';' + writeLine
                    newFile.write(writeLine)
                    print 'file %s, line %s replaced with %s' %(oldFile, line, writeLine)
                elif newLine[1:] in line:
                    writeLine = '%s\n' %newLine
                    writeLine = writeLine.lstrip(';')
                    writeLine = writeLine.lstrip('*')
                    newFile.write(writeLine)
                    print 'file %s, line %s replaced with %s' %(oldFile, line, writeLine)
                else:
                    newFile.write(line)
        finally:
            oldFile.close()
            newFile.close()
        shutil.copy(fileNameTmp, self.file)

class plcEventBox(gtk.EventBox, _plcSymbol):
    """
    This class can change the style by plc symbol
    """
    def __init__(self, plcSymbol, styleDict):
        """
        Parameter
            plcSymbol : plc symbol which chose the style
            styleDict : dictionary with connection between the plc symbol and the style name from OemGtkStyle.rc

            eBox = plcEventBox(plcSymbol='WG_workpiece_counter', styleDict={1:'widgetToolDataValue',2:'embeddedWindowHeader',3:'info'})
            eventLabel = gtk.Label('Hello')
            eBox.add(eventLabel)
            myWindow.pack_start(eBox)
        """
        self.styleDict = styleDict
        gtk.EventBox.__init__(self)
        identPlcSymbol = GLOBAL_SYMBOL + plcSymbol
        self.subscribeToPlc( ident=identPlcSymbol )

    def _onPlcSymbolChanged(self, plcValueDict, event=None):
        """
        This method runs when the plc symbol changed the value
        """
        #print 'INFO %s::%s() data:%s' %(__name__, sys._getframe().f_code.co_name, plcValueDict)
        newValue = plcValueDict.values()[0]
        styleName = self.styleDict.get(newValue)
        if styleName:
            self.set_name(styleName)


class JhDictTreeView(gtk.TreeView):
    """
    returns a TreeView widget, which can be filled with dictionaries

    Parameter
        dictPrimaryKey            : the primaryKey of the dictionary (which have to be unique)
        columnOrderNames          : a list of column names, which defines the sorting and visible columns of the table
        tableIdent                : Ident path of the file
        notifyOnChanged           : callback function of changed data in treeView
        notifyOnSelectingChanged  : callback function of selected row changed
        defaultColumnNameIfEmpty  : columnname which will be set if no data is given

    Example
        treeView = JhDictTreeView(dictPrimaryKey='a',
                                  columnOrderNames=['a', 'b'],
                                  notifyOnSelectingChanged=selecting_changed_callback,
                                  notifyOnChanged=changed_data_callback)

        treeView.addRow({'a':'1', b:'2', c:'3'}
        treeView.addRow({'a':'2', b:'A', c:'B'}

        def selecting_changed_callback(dataDict, treeView):
            print(dataDict)

        def changed_data_callback(dataDict, event, treeView):
            print(dataDict, event)
    """
    def __init__(self, dictPrimaryKey, columnOrderNames=[],  notifyOnChanged=None, notifyOnSelectingChanged=None, defaultColumnNameIfEmpty="No entries"):
        self.model = None
        self._columnNameList = None

        self._TableRowmodelRowjhDict = {}
        self._dictPrimaryKey = dictPrimaryKey
        self._notifyOnChanged = notifyOnChanged
        self._notifyOnSelectingChanged = notifyOnSelectingChanged
        self._defaultColumnNameIfEmpty = defaultColumnNameIfEmpty

        if columnOrderNames is None:
            self._columnOrderNames = []
        else:
            self._columnOrderNames = columnOrderNames

        gtk.TreeView.__init__(self)

        if self.model is None:
            self._setDefaultModel()
            self._clearAndSetColumns(columnNameList=self._columnNameList, ColumnNameIfnone=defaultColumnNameIfEmpty)

    def _setDefaultModel(self):
        """
        sets the data model, with a default row entry
        """
        # datatype for each column
        model = gtk.ListStore(str)

        #model needs one element
        model.append([""])

        # set to TreeView
        self.set_model(model)

    def _clearAndSetColumns(self, columnNameList, ColumnNameIfnone):
        """
        set the columns heads in the treeview from _columnNameList from parameter
        """
        #resets the columns
        self._clearColumns()

        if columnNameList is None:
            #Default if no table could be attached
            self._setColumnsFromList([ColumnNameIfnone])
        else:
            # set the columnames from list
            self._setColumnsFromList(columnNameList)

    def _clearColumns(self):
        """
        clears the Columns of the TreeView
        """
        columnsList = []

        try:
            columnsList = self.get_columns()
        except Exception:
            return

        for column in columnsList:
            if column:
                self.remove_column(column)

    def _setColumnsFromList(self, columnNameList):
        """
        sets the Columns name from _columnNameList
        """
        # set CellRender for column to display, default Text
        render = gtk.CellRendererText()

        columnIndex = 0
        for columnName in columnNameList:
            column = gtk.TreeViewColumn(columnName, render, text=columnIndex)

            #hide column if not defined in self._columnNameList
            if len(self._columnOrderNames) > 0:
                if columnName not in self._columnOrderNames:
                    column.set_visible(False)

            columnIndex += 1
            self.append_column(column)

    def _checkPrimaryKeyInDict(self, dataDict):
        """
        returns Boolean if primarykey was found in dataDict
        """
        isKeyinDict = self._dictPrimaryKey in dataDict
        return isKeyinDict

    def addRow(self, dataDict):
        """
        adds a row to the table
        """
        if self.model is None:
            self._createModelAndSortColumnNameFromDict(dataDict)
            self._clearAndSetColumns(self._columnNameList, self._defaultColumnNameIfEmpty)

        #allready in rows - then make a change
        if self._checkPrimaryKeyInDict:
            if self._getTreeIterFromDict(dataDict):
                print("Error addRow() primaryKey allready in table data", dataDict)
                return

        #get sorted valuesList
        valuesList = self._getListfromDictionaryByColumNameList(self._columnNameList, dataDict)
        treeIter = self.model.append(valuesList)

        if treeIter:
            #add the new record with the primaryKey
            primaryKeyName = self._dictPrimaryKey
            if primaryKeyName in dataDict:
                rowPrimaryKeyValue = dataDict[primaryKeyName]
                self._TableRowmodelRowjhDict[rowPrimaryKeyValue] = treeIter

                if self._notifyOnChanged and callable(self._notifyOnChanged):
                    self._notifyOnChanged(dataDict, jh.notify.INSERT, self)
            else:
                print("Error addRow() no PrimaryKey in table data", dataDict)

    def changeRow(self, dataDict):
        """
        changes a row if its in the table
        """
        treeIter = self._getTreeIterFromDict(dataDict)

        if treeIter:
            #create pair of column number and value
            parameterList = []
            columnIndex = 0

            for value in self._getListfromDictionaryByColumNameList(self._columnNameList, dataDict):
                parameterList.append(columnIndex)
                parameterList.append(value)
                columnIndex += 1

            self.model.set(treeIter, *parameterList)

            if self._notifyOnChanged and callable(self._notifyOnChanged):
                self._notifyOnChanged(dataDict, jh.notify.CHANGE, self)

    def removeRow(self, dataDict):
        """
        removes a row if its in the table
        """
        treeIter = self._getTreeIterFromDict(dataDict)

        if treeIter:
            self.model.remove(treeIter)
            # remove from mapping
            self._TableRowmodelRowjhDict.pop(dataDict[self._dictPrimaryKey])

            if self._notifyOnChanged and callable(self._notifyOnChanged):
                self._notifyOnChanged(dataDict, jh.notify.DELETE, self)
        else:
            print("Error: removeRow() wasnt found", dataDict)

    def _getTreeIterFromDict(self, dataDict):
        """
        return the treeIter if found
        else None
        """
        treeiter = None

        if self._dictPrimaryKey in dataDict:
            if dataDict[self._dictPrimaryKey] in self._TableRowmodelRowjhDict:
                treeiter = self._TableRowmodelRowjhDict[dataDict[self._dictPrimaryKey]]

        return treeiter

    def _createModelAndSortColumnNameFromDict(self, dataDict):
        """
        sorts the dataDict keys as list
        and initialize the model
        """
        self._columnNameList = dataDict.keys()
        self._columnNameList.sort()

        #set primary key in first place
        self._columnNameList.remove(self._dictPrimaryKey)
        self._columnNameList.insert(0, self._dictPrimaryKey)

        #set DOC to last
        if 'DOC' in self._columnNameList:
            indexDoc = self._columnNameList.index('DOC')
            if self._columnNameList.pop(indexDoc):
                self._columnNameList.append('DOC')

        if len(self._columnOrderNames) > 0:
            tmplist = []
            tmpOriginalColumNamelist = self._columnNameList[:]

            for columname in self._columnOrderNames:
                if columname in tmpOriginalColumNamelist:
                    tmplist.append(columname)
                    tmpOriginalColumNamelist.remove(columname)

            for columname in tmpOriginalColumNamelist:
                tmplist.append(columname)

            self._columnNameList = tmplist

        self._initializeModelFromColumnNameList(self._columnNameList)

    def _initializeModelFromColumnNameList(self, columnNameList, defaultType=str):
        """
        initializes the Model from _columnNameList with the columnype of defaultType
        """
        if self.model is None:

            #list of types for the column count
            typeList = []

            for items in columnNameList:
                typeList.append(str)

            self.model = gtk.ListStore(*typeList)
            self.set_model(self.model)

            # connect signal to event handler
            # row select change event
            if self._notifyOnSelectingChanged:
                self.get_selection().connect("changed" , self._SelectionChangedCallback)

    def _SelectionChangedCallback(self, selection):
        """
        callback function which will be called on selection change
        and calls if not None the notifyOnSelectiongChanged callback function
        """
        model, paths = selection.get_selected_rows()

        if paths:
            tableDataDict = self.getRowDictionaryFromRowPath(paths[0])
            if tableDataDict:
                if self._notifyOnSelectingChanged and callable(self._notifyOnSelectingChanged):
                    self._notifyOnSelectingChanged(self, tableDataDict)

    def _getDictionaryFromIter(self,iter):
        ret = None

        if iter:
            #model.get need column indizes
            indixList = range(0, len(self._columnNameList))
            valueList = self.model.get(iter, *indixList)

            ret = dict(zip(self._columnNameList, valueList))

        return ret

    def getRowDictionaryFromRowPath(self, path):
        """
        retrievs row data from model
        returns a dictionary with key=column and value is the data
        returns None if no row was found
        """
        ret = None

        if self.model:
            iter = self.model.get_iter(path)
            ret = self._getDictionaryFromIter(iter)

        return ret

    def _getListfromDictionaryByColumNameList(self, columnNameList, dataDict):
        """
        returns a list from the dataDict, which will be sorted through _columnNameList
        """
        newList = []

        for columnName in columnNameList:
            if columnName in dataDict:
                newList.append(dataDict[columnName])
            else:
                newList.append("")

        return newList

    def hasRows(self):
        """
        return True if the model has a minimum of one row else False
        """
        ret = False

        if self.model:
            ret = len(self.model) > 0

        return ret

    def getSelectedRowAsDictionary(self):
        """
        returns a dictionary from the selected row else None
        """
        model, iter = self.get_selection().get_selected()

        ret = self._getDictionaryFromIter(iter)

        return ret

class JhTableListView(JhDictTreeView):
    """
    This class creates a widget with data of a table format file like *.tab *.t *.p

    further documentation in class JhDictTreeView

    Parameter
        tableIdent                : Ident path of the file
        primaryKey                : the primaryKey of the file (default 'NR')
        columnOrderNames          : a list of column names, which defines the sorting and visibility of the columns of the table
        tableIdent                : Ident path of the file
        notifyOnChanged           : callback function of changed data in treeView
        notifyOnSelectingChanged  : callback function of selected row changed
        defaultColumnNameIfEmpty  : columnname which will be set if no data is given

    Example
        treeView = JhTableListView(tableIdent="\\TABLE\\'PLC:\\proto\\table\\AFC.TAB'",
                                    primaryKey='AFC',
                                    columnOrderNames=['AFC', 'FMIN','FMAX'],
                                    notifyOnSelectingChanged=selecting_changed_callback,
                                    notifyOnChanged=changed_data_callback)

        def selecting_changed_callback(dataDict, treeView):
            print(dataDict)

        def changed_data_callback(dataDict, event, treeView):
            print(dataDict, event)
    """
    def __init__(self, tableIdent, primaryKey='NR', columnOrderNames=[], notifyOnChanged=None, notifyOnSelectingChanged=None, defaultColumnNameIfEmpty="No entries"):
        #initialize the dictionary TreeView
        JhDictTreeView.__init__(self, dictPrimaryKey=primaryKey,
                                columnOrderNames=columnOrderNames,
                                notifyOnChanged=notifyOnChanged,
                                notifyOnSelectingChanged=notifyOnSelectingChanged,
                                defaultColumnNameIfEmpty=defaultColumnNameIfEmpty)

        # attach the JhTable class
        # All existing rows will be filled over the notifyOnChanged into the treeview model
        self.tab = JhTable(ident=tableIdent, notify=self._onTableChanged)

    def _onTableChanged (self, data, event=None):
        """
        change event from JhTable
        """
        if event and data:
            if event == jh.notify.INSERT or event == jh.notify.INIT:
                self.addRow(data)
            elif event == jh.notify.CHANGE or jh.notify.MULTI:
                self.changeRow(data)
            elif event == jh.notify.DELETE:
                self.removeRow(data)
            else:
                print '%s not handled' %event


