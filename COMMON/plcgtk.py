#! /usr/bin/env python
# -*- coding: UTF-8 -*-
"""
This module contains a collection of common plcgtk  classes.

Author: JH PLC-Service / MCE / +49 (8669) 31-3102 / service.plc@heidenhain.de
"""
PLC_GTK_VERSION = '5.1'

# IMPORT MODULS
#-----------------------------------------------------------
import pygtk
pygtk.require( '2.0' )
import gtk          # gtk functions

import pyjh         # JH interface, version
pyjh.require( '3.2' )
import jh           # import jh interface for event loop
import jh.gtk       # jh.gtk class incl. window-registration
import jh.gtk.glade # import jh glade interface
import jh.pango     # jh.pango fonts
import pango        # pango fonts

import sys          # system functions
import gobject      # global objects

# GLOBAL DEFINITIONS
#-----------------------------------------------------------
GLOBAL_SYMBOL       =  '\\PLC\\program\\symbol\\global\\'

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
    """
    instanceCounter = 0

    #def __init__(self,usage='PLCmedium', title='PLC WINDOW', logo = 'PLC:\Python\PICTURE\logo.gif', focus = False, setTransient=True, padding = 1, plcSymbol = None, notify = None, styleName = 'embeddedWindowHeader'):
    def __init__(self,usage='PLCmedium', title='PLC WINDOW', logo = None, focus = False, setTransient=True, padding = 1, plcSymbol = None, notify = None, styleName = 'embeddedWindowHeader'):
        embeddedWindow.instanceCounter += 1
        print 'INFO %s.%s() <%s> [%s]' %(type(self).__name__, sys._getframe().f_code.co_name, plcSymbol, embeddedWindow.instanceCounter)

        self.usage          = usage
        self.title          = title
        self.logo           = logo
        self.focus          = focus
        self.setTransient   = setTransient
        self.padding        = padding
        self.plcSymbol      = plcSymbol
        self.notify         = notify

        self.window         = None
        self.firstChild     = None
        self.identplcSymbol = None
        self.handleplcSymbol= None

        # define the window style
        gtk.rc_parse( './LAYOUT/OemGtkStyle.rc'  )

        #create the widgets
        self.ScrolledWindow = gtk.ScrolledWindow(hadjustment=None, vadjustment=None)
        self.ScrolledWindow.set_policy(hscrollbar_policy=gtk.POLICY_AUTOMATIC, vscrollbar_policy=gtk.POLICY_AUTOMATIC)

        self.Viewport = gtk.Viewport()
        self.Viewport.set_shadow_type(gtk.SHADOW_OUT)

        self.VBox = gtk.VBox(homogeneous=False, spacing=0)
        self.HBox = gtk.HBox(homogeneous=False, spacing=10)

        self.headerEventBox = gtk.EventBox()
        if styleName is not None:
            self.headerEventBox.set_name(styleName)

        self.headerHBox = gtk.HBox(homogeneous=False, spacing=0)

        if self.logo is not None:
            image = gtk.Image()
            image.set_from_file(jh.ResPath(self.logo))
            #self.set_alignment(0.0, 0.0)
            image.set_padding(xpad = 1, ypad = 1)

            self.headerHBox.pack_start(image, expand = False, fill = False, padding = 0)

        if self.title is not None:
            titleLabel = gtk.Label(title)
            titleLabel.set_alignment(0.0, 0.5)
            titleLabel.set_padding(xpad = 3, ypad = 0)

            #titleLabel.set_property( 'xalign' , 0 )
            if styleName is not None:
                titleLabel.set_name(styleName)
            self.headerHBox.pack_start(titleLabel, expand = False, fill = False, padding = 0)

        self.headerEventBox.add(self.headerHBox)
        self.pack_start(self.headerEventBox, padding = 1)

        self.HBox.pack_start(self.VBox, padding = self.padding)
        self.Viewport.add(self.HBox)
        self.ScrolledWindow.add(self.Viewport)

        self.firstChild = self.ScrolledWindow

        # subscribe to plc symbol or show the window immediately
        if self.plcSymbol is not None:
            self.identplcSymbol = GLOBAL_SYMBOL + self.plcSymbol
            self.handleplcSymbol = jh.Subscribe(ident=self.identplcSymbol, notify=self._onPlcSymbolChanged, onChange=True)
        else:
            self._showWindow()

    def __del__(self):
        """ destructor """
        print 'INFO %s.%s() <%s> [%s]' %(type(self).__name__, sys._getframe().f_code.co_name, self.plcSymbol, embeddedWindow.instanceCounter)
        embeddedWindow.instanceCounter -= 1

    def _onPlcSymbolChanged(self, plcValueDict, event=None):
        """
        This method runs when the plc symbol changed the value
        """
        #print 'INFO %s::%s() data:%s' %(__name__, sys._getframe().f_code.co_name, plcValueDict)
        newValue = plcValueDict.values()[0]
        if newValue is not None:
            if newValue == True:
                self._showWindow()
            else:
                self._destroyWindow()

            if self.notify is not None and callable(self.notify):
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
            self.window.connect("destroy", self._destroyWindow)
            self.window.add( self.firstChild)

        self.window.show_all( )

        if self.focus == True:
            self.getFocus()

    def _destroyWindow(self,widget=None):
        """
        Remove the child from the window and destroy the window
        """
        if self.window is not None:
            child = self.window.get_child()
            if child:
                self.window.remove(child)
            self.window.destroy()
            self.window = None
            self.leaveFocus()

    def changeUsage(self, usage):
        """
        change the usage of the window
        """
        self._destroyWindow()
        self.usage = usage
        self._showWindow()

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
        if self.window is not None:
            self.window.Focus(jh.focus.GET)

    def leaveFocus(self):
        """
        Leave the focus
        """
        if self.window is not None:
            self.window.Focus(jh.focus.LEAVE)

    def getScreenWidth(self):
        """
        Get screen width
        """
        if self.window is not None:
            return self.ScrolledWindow.get_screen().get_width()
        else:
            return None

class keycodeWindow(embeddedWindow):
    """
    this class creates a window to enter and check a specific keycode. If the keycode is correct the callback function wil be notifyed with True. If not False.    
    """
    instanceCounter = 0
    def __init__(self, keycode, callback, title='', logo = 'PLC:\Python\PICTURE\logo.gif', infoText=None, infoLogo=gtk.STOCK_DIALOG_QUESTION, screen='MachineScreen'):
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
        print 'INFO %s.%s() [%s]' %(type(self).__name__, sys._getframe().f_code.co_name, keycodeWindow.instanceCounter)

        self.keycode = keycode
        self.callback = callback
        
        embeddedWindow.__init__(self, usage='', title=title, logo = logo, focus = True, setTransient=True, padding = 1, plcSymbol = None, notify = None, styleName = 'embeddedWindowHeader')
        self.window.window.set_decorations( gtk.gdk.DECOR_BORDER | gtk.gdk.DECOR_TITLE )
        #self.window.window.set_functions( gtk.gdk.FUNC_MOVE | gtk.gdk.FUNC_RESIZE )
        self.window.set_modal(True)                
        self.window.resize(400,150) 
                    
        if infoText:
            self.pack_start(info(text=infoText, stockIcon=infoLogo))
        
        keyEntry = gtk.Entry() 
        keyEntry.set_invisible_char('*')   
        keyEntry.set_visibility(False)    
        keyEntry.connect("activate", self.onEntryActivate)        
        self.pack_start(keyEntry)
        keyEntry.grab_focus()
                
    def __del__(self):
        print 'INFO %s.%s() [%s]' %(type(self).__name__, sys._getframe().f_code.co_name, keycodeWindow.instanceCounter)
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
        print 'INFO %s.%s() [%s]' %(type(self).__name__, sys._getframe().f_code.co_name, table.instanceCounter)
        table.instanceCounter += 1
        gtk.Table.__init__(self, rows=rows, columns=columns, homogeneous=homogeneous)

    def __del__(self):
        """ destructor """
        print 'INFO %s.%s() [%s]' %(type(self).__name__, sys._getframe().f_code.co_name, table.instanceCounter)
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
    def __init__(self, text, stockIcon = gtk.STOCK_INFO, text_border_width=10, styleName = 'info'):
        info.instanceCounter += 1
        print 'INFO %s.%s() [%s]' %(type(self).__name__, sys._getframe().f_code.co_name, info.instanceCounter)

        gtk.HBox.__init__(self, homogeneous=False, spacing=0)
        self.set_name(styleName)

        if stockIcon is not None:
            iconEventBox = gtk.EventBox()
            if styleName is not None:
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

        if styleName is not None:
            self.infoTextView.set_name(styleName)

        self.textbuffer = self.infoTextView.get_buffer()
        self.textbuffer.set_text(self.text)

    def __del__(self):
        print 'INFO %s.%s() [%s]' %(type(self).__name__, sys._getframe().f_code.co_name, info.instanceCounter)
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
            if self.plcAlias is not None:
                newValue = self.plcAlias.get(value)
                if newValue is not None:
                    return str(newValue)

            if (type(value) is not str) and (self.plcFactor is not None):
                value *= self.plcFactor

            if self.plcFormat is None:
                return str(value)
            else:
                return str(self.plcFormat %value)
        except Exception,msg:
            print 'EXCEPT %s::%s wrong plcFormat (msg:%s)' %(__name__, sys._getframe().f_code.co_name, msg)
            return None

    def _callback(self, value):
        """
        callback the self.notify function
        """
        if self.notify is not None and callable(self.notify):
            self.notify( value )

    def subscribeToPlc(self, ident, downTime=0.2):
        """
        subscribe to plc symbol an connect to _onPlcSymbolChanged
        """
        self.handlePlcSymbol = jh.Subscribe(ident=ident, notify=self._onPlcSymbolChanged, downTime=downTime, onChange=True)

    def unSubscribeFromPlc(self):
        """
        unsubscribe from plc symbol
        """
        if self.handlePlcSymbol is not None:
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
        styleName    : Widgets can be named, which allows you to refer to them in a GTK resource file

    Example:
        myPlcCheckButtons = plcCheckButtons( plcSymbol='DG_checkButtons' , labels=['X','Y','Z',4,5,6,7,8,9,10], notify = self.onCB )
        self.myWindow.add( myPlcCheckButtons )
    """
    instanceCounter = 0
    def __init__(self, labels, plcSymbol, initValue = None, notify = None, wrap=8, xpad = 1, ypad=0, styleName = 'plcCheckButtons'):
        plcCheckButtons.instanceCounter += 1
        print 'INFO %s.%s() <%s> [%s]' %(type(self).__name__, sys._getframe().f_code.co_name, plcSymbol, plcCheckButtons.instanceCounter)

        self.plcSymbol = plcSymbol.strip()
        self.notify = notify

        gtk.Table.__init__(self)
        self.set_homogeneous(False)

        self.numberOfCheckButtons = len(labels)

        numberOfRows = (self.numberOfCheckButtons / wrap + 1) + 1
        numberOfLastColumns = self.numberOfCheckButtons%wrap

        self.handlePlcSymbol = None

        idx=0
        self.checkButtonDict={}
        try:
            for row in range(0,numberOfRows):
                for col in range(0,wrap):
                    vBox = gtk.VBox()

                    label = str(labels.pop(0))
                    newLabel = gtk.Label(str=label)
                    newLabel.set_padding(xpad, ypad)
                    newLabel.set_alignment(xalign=0.5, yalign=0.5)
                    if styleName is not None:
                        newLabel.set_name(styleName)

                    newCheckbutton = gtk.CheckButton(label=None, use_underline=True)
                    newCheckbutton.connect('toggled', self.on_checkButtonToggled, idx )
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
            if initValue is not None:
                self.putValue(initValue)

    def __del__(self):
        """ destructor """
        print 'INFO %s.%s() <%s> [%s]' %(type(self).__name__, sys._getframe().f_code.co_name, self.plcSymbol, plcCheckButtons.instanceCounter)
        plcCheckButtons.instanceCounter -= 1

    def _onPlcSymbolChanged(self, plcValueDict, event=None):
        """
        This method runs when the plc symbol changed the value
        """
        #print 'INFO %s::%s() data:%s' %(__name__, sys._getframe().f_code.co_name, plcValueDict)
        plcValueDec = plcValueDict.values()[0]
        for idx in range(self.numberOfCheckButtons-1,-1,-1):
            widget = self.checkButtonDict[idx]
            widgetState = widget.get_active()
            pot = 2**(idx)
            if plcValueDec / pot > 0:
                newState = True
                plcValueDec -= pot
            else:
                newState = False

            if widgetState != newState:
                widget.set_active(newState)

    def on_checkButtonToggled(self, widget,idx ):
        """
        This method runs when any checkbutton toggled
        """
        #print 'INFO %s::%s() %s IDX:%s' %(__name__, sys._getframe().f_code.co_name, widget, idx)

        if self.handlePlcSymbol == None:
            return

        checkAxisName = widget.name
        if widget.get_active(): idxValue = '1'
        else: idxValue = '0'

        plcSymbolRet = jh.Get(self.handlePlcSymbol)
        if plcSymbolRet is not None:

            plcValueDec = plcSymbolRet.values()[0]
            binStr = ''
            for runIdx in range(self.numberOfCheckButtons,-1,-1):
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
            print 'ERRORR %s::%s()jh.Put {%s:%s} /n    ret:%s, No:%s Str:%s ' %(__name__, sys._getframe().f_code.co_name, self.identPlcSymbol,  value, ret , jh.Errno(),jh.Errstr() )

        if self.notify is not None and callable(self.notify):
            self.notify( value )

class plcButton():
    """
    wie check button
    """
    pass

class plcCheckButton(gtk.CheckButton, _plcSymbol):
    """
    This class returns a widget with plc check buttons.

    Parameter
        plcSymbol   : plc symbol to connect (M)
        label       : define a label
        initValue   : initial value
        notify      : callbackfunktion that get the notification of a new value
        sensetive   : If sensitive is True the widget will be sensitive and the user can interact with it
        styleName    : Widgets can be named, which allows you to refer to them in a GTK resource file
    """
    instanceCounter = 0
    def __init__(self, plcSymbol, label = None, initValue = None, notify = None, sensetive = True, styleName = 'plcCheckButton'):
        plcCheckButton.instanceCounter += 1
        print 'INFO %s.%s() <%s> [%s]' %(type(self).__name__, sys._getframe().f_code.co_name, plcSymbol, plcCheckButton.instanceCounter)

        self.plcSymbol = plcSymbol.strip()
        self.notify = notify

        gtk.CheckButton.__init__(self,label=label)

        self.set_alignment(0.0,0.0)
        self.set_sensitive(sensetive)
        if styleName is not None:
            self.set_name(styleName)
        self.identPlcSymbol = GLOBAL_SYMBOL + self.plcSymbol
        self.subscribeToPlc( ident=self.identPlcSymbol )

        self.connect('toggled', self.on_checkButtonToggled )

        if initValue is not None:
            self.set_active(initValue)
        self.toggled()

    def __del__(self):
        """ destructor """
        print 'INFO %s.%s() <%s> [%s]' %(type(self).__name__, sys._getframe().f_code.co_name, self.plcSymbol, plcCheckButton.instanceCounter)
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

    def on_checkButtonToggled(self, widget ):
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

        if self.notify is not None and callable(self.notify):
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
        print 'INFO %s.%s() <%s> [%s]' %(type(self).__name__, sys._getframe().f_code.co_name, plcSymbol, plcEntry.instanceCounter)
        self.plcSymbol  = plcSymbol.strip()
        self.plcFactor  = plcFactor
        self.plcFormat  = plcFormat
        self.plcAlias   = plcAlias
        self.minValue   = minValue
        self.maxValue   = maxValue
        self.notify     = notify
        self.oldText    = ''

        if self.plcAlias is not None:
            editable = False

        gtk.Entry.__init__(self, maxLength)
        self.set_editable(editable)
        if editable is False:
            self.unset_flags(gtk.CAN_FOCUS)
        self.set_sensitive(sensitive)
        self.set_size_request(width=width, height=height)

        if styleName is not None:
            self.set_name(styleName)

        if baseColor is not None:
            self.modify_base(state = gtk.STATE_NORMAL, color = gtk.gdk.color_parse(baseColor))

        if textColor is not None:
            self.modify_text(state = gtk.STATE_NORMAL, color = gtk.gdk.color_parse(textColor))

        self.identPlcSymbol = GLOBAL_SYMBOL + self.plcSymbol
        self.subscribeToPlc( ident=self.identPlcSymbol )

        self.connect('activate', self.onEntryActivate )
        self.connect('changed', self.onChanged)

        if len(initValue) > 0:
            self.set_text(initValue)

        self.activate()

    def __del__(self):
        """ destructor """
        print 'INFO %s.%s() <%s> [%s]' %(type(self).__name__, sys._getframe().f_code.co_name, self.plcSymbol, plcEntry.instanceCounter)
        plcEntry.instanceCounter -= 1

    def onChanged(self, *args):
        """
        this value runs when the value has chanced.
        if the entry is digit, except only digits.
        """
        if self.plcFactor is not None and self.plcAlias is None:
            text = self.get_text().strip()
            text = ''.join([i for i in text if i in '0123456789.'])
            text = self._formatValue(text)
            self.set_text(text)

    def onEntryActivate(self, widget, event=None):
        """
        this method runs when the operator activate the entry
        """
        #print 'INFO %s::%s() ' %(__name__, sys._getframe().f_code.co_name)

        if self.plcAlias is not None:
            return

        newValue = self.get_text()

        try:
            if self.plcFactor is not None:
                newValue = float(newValue)
                if self.minValue is not None and newValue < self.minValue:
                    # fehler min max anzeigen
                    raise
                if self.maxValue is not None and newValue > self.maxValue:
                    # fehler min max anzeigen
                    raise
                newValue = int(round(newValue / self.plcFactor))

        except Exception, msg:
            print 'EXCEPT %s::%s wrong plcFactor (msg:%s)' %(__name__, sys._getframe().f_code.co_name, msg)
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
        plcSymbol   : plc symbol to connect (M)
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
        print 'INFO %s.%s() <%s> [%s]' %(type(self).__name__, sys._getframe().f_code.co_name, plcSymbol, plcLabel.instanceCounter)
        self.plcSymbol  = plcSymbol
        self.plcFactor  = plcFactor
        self.plcFormat  = plcFormat
        self.plcAlias   = plcAlias
        self.notify     = notify
        self.preText    = preText
        self.postText   = postText
        self.valueLength= 1

        gtk.Label.__init__(self,initValue)
        self.set_alignment(0.0, 0.0)
        self.set_padding(xpad = 0, ypad = 0)

        if styleName is not None:
            self.set_name(styleName)

        if textColor is not None:
            self.modify_fg(state = gtk.STATE_NORMAL, color = gtk.gdk.color_parse(textColor))

        if self.plcSymbol is not None:
            self.identPlcSymbol = GLOBAL_SYMBOL + self.plcSymbol.strip()
            self.subscribeToPlc( ident=self.identPlcSymbol )

    def __del__(self):
        """ destructor """
        print 'INFO %s.%s() <%s> [%s]' %(type(self).__name__, sys._getframe().f_code.co_name, self.plcSymbol, plcLabel.instanceCounter)
        plcLabel.instanceCounter -= 1

    def _onPlcSymbolChanged(self, plcValueDict, event=None):
        """
        This method runs when the plc symbol changed the value
        """
        #print 'INFO %s::%s() data:%s' %(__name__, sys._getframe().f_code.co_name, plcValueDict)
        newValue = plcValueDict.values()[0]
        newText = self._formatValue(newValue)
        self.set_text('%s%s%s' %(self.preText,newText,self.postText))

        self._callback(newValue)

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
        print 'INFO %s.%s() <%s> [%s]' %(type(self).__name__, sys._getframe().f_code.co_name, plcSymbol, plcLevelBar.instanceCounter)
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

        if styleName is not None:
            self.set_name(styleName)

        if self.textColor is not None:
            self.modify_fg(state = gtk.STATE_NORMAL, color = gtk.gdk.color_parse(self.textColor))    # Text

        #self.modify_bg(state = gtk.STATE_NORMAL, color = gtk.gdk.color_parse('black'))   # Background
        #self.modify_bg(state = gtk.STATE_PRELIGHT, color = gtk.gdk.color_parse('green')) # bar

        if initValue is not None:
            self.setLevel(initValue)

        self.identPlcSymbol = GLOBAL_SYMBOL + self.plcSymbol
        self.subscribeToPlc( ident=self.identPlcSymbol )

    def __del__(self):
        """ destructor """
        print 'INFO %s.%s() <%s> [%s]' %(type(self).__name__, sys._getframe().f_code.co_name, self.plcSymbol, plcLevelBar.instanceCounter)
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
        if self.barColors is not None:
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
        fraction = 1.0 / self.maxValue * newValueWithFactor

        if fraction < 0:
            fraction=0
        self.set_fraction(fraction)


class plcImage(gtk.Image, _plcSymbol):
    """
    This class returns a plc gtk.Image.

    Parameter
        plcSymbol   : plc symbol to connect (M)
        ertweiterung auf INT , evtl als dict wie bei der levelbar
        notify      : callback function that get the notification of a new value
        imageTrue   : image (*.bmp *.jpg *.gif, ...) that will show on True
        imageFalse  : image (*.bmp *.jpg *.gif, ...) that will show on False
    """
    instanceCounter = 0
    def __init__(self, plcSymbol, notify = None, imageTrue = gtk.STOCK_YES, imageFalse = gtk.STOCK_NO):
        plcImage.instanceCounter += 1
        print 'INFO %s.%s() <%s> [%s]' %(type(self).__name__, sys._getframe().f_code.co_name, plcSymbol, plcImage.instanceCounter)
        self.plcSymbol  = plcSymbol.strip()
        self.notify     = notify
        self.imageTrue  = imageTrue
        self.imageFalse = imageFalse

        gtk.Image.__init__(self)

        self.set_padding(xpad = 0, ypad = 0)

        self.imageType = None
        if imageTrue[:4].upper() == 'GTK-':
            self.imageType = 'STOCK_ICON'
        elif imageTrue[-4:].upper() in ('.BMP','.PNG','.GIF','.JPG'):
            self.imageType = 'FILE'
            self.imageTrue = jh.ResPath(self.imageTrue)
            self.imageFalse = jh.ResPath(self.imageFalse)

        self.identPlcSymbol = GLOBAL_SYMBOL + self.plcSymbol
        self.subscribeToPlc( ident=self.identPlcSymbol )

    def __del__(self):
        """ destructor """
        print 'INFO %s.%s() <%s> [%s]' %(type(self).__name__, sys._getframe().f_code.co_name, self.plcSymbol, plcImage.instanceCounter)
        plcImage.instanceCounter -= 1

    def _onPlcSymbolChanged(self, plcValueDict, event=None):
        """
        this method runs when the plc symbol changed the value
        """
        #print 'INFO %s::%s() data:%s' %(__name__, sys._getframe().f_code.co_name, plcValueDict)
        newState = plcValueDict.values()[0]
        if newState == False:
            image = self.imageFalse
        else:
            image = self.imageTrue

        if self.imageType == 'STOCK_ICON':
            self.set_from_stock(image, gtk.ICON_SIZE_SMALL_TOOLBAR )
        elif self.imageType == 'FILE':
            self.set_from_file(filename=image)
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
    def __init__(self, plcSymbol, notify = None, label = None, labelPos = 'LEFT', imageTrue = gtk.STOCK_YES, imageFalse = gtk.STOCK_NO, styleName = 'plcImageWithLabel'):
        plcImageWithLabel.instanceCounter += 1
        print 'INFO %s.%s() <%s> [%s]' %(type(self).__name__, sys._getframe().f_code.co_name, plcSymbol, plcImageWithLabel.instanceCounter)
        self.plcSymbol  = plcSymbol.strip()
        self.imageTrue  = imageTrue
        self.imageFalse = imageFalse

        gtk.Table.__init__(self, rows=3, columns=3, homogeneous=False)
        if label is not None:
            label = gtk.Label(label)

            if styleName is not None:
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

        self.image = plcImage( plcSymbol = plcSymbol, notify = notify, imageTrue = imageTrue, imageFalse = imageFalse )
        #self.image = gtk.Image()
        self.attach(child=self.image, left_attach=2, right_attach=3, top_attach=2, bottom_attach=3,  xoptions=gtk.SHRINK, yoptions=gtk.SHRINK, xpadding=0, ypadding=0)

    def __del__(self):
        """ destructor """
        print 'INFO %s.%s() <%s> [%s]' %(type(self).__name__, sys._getframe().f_code.co_name, self.plcSymbol, plcImageWithLabel.instanceCounter)
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
        print 'INFO %s.%s() <%s> [%s]' %(type(self).__name__, sys._getframe().f_code.co_name, plcSymbol, plcLineGraph.instanceCounter)
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

        if styleName is not None:
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

    def __del__(self):
        """ destructor """
        print 'INFO %s.%s() <%s> [%s]' %(type(self).__name__, sys._getframe().f_code.co_name, self.plcSymbol, plcLineGraph.instanceCounter)
        plcLineGraph.instanceCounter -= 1

    def area_expose_cb(self, area, event):
        """
        callback function for redrawing the area on a "expose-event" event
        """
        if self.exposed == False:
            for graph in self.graphList:
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
            #self.gcHelpline.set_rgb_bg_color(gtk.gdk.color_parse('white'))

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
            if plcFactor is not None and type(newValue) != str:
                newValueWithFactor = newValue * plcFactor
                valuesList.append(newValueWithFactor)
            else:
                valuesList.append(newValue)

            # reduce list length
            if len(valuesList) > self.listLength:
                #popLength = int(len(valuesList)*0.2)
                #graph.values = valuesList[popLength:]
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

        if self.helpLines is not None:
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
            self.window.draw_lines(gc, points)

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
        print 'INFO %s.%s() <%s> [%s]' %(type(self).__name__, sys._getframe().f_code.co_name, plcSymbol, _graph.instanceCounter)
        self.plcSymbol  = plcSymbol.strip()
        self.values     = []
        self.plcFactor  = plcFactor
        self.plcFormat  = plcFormat
        self.notify     = notify
        self.color      = color
        self.showText   = showText
        self.preText    = preText
        self.postText   = postText

    def __del__(self):
        """ destructor """
        print 'INFO %s.%s() <%s> [%s]' %(type(self).__name__, sys._getframe().f_code.co_name, self.plcSymbol, _graph.instanceCounter)
        _graph.instanceCounter -= 1
