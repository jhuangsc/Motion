## [insertprogramname] 
##   by Jonathan Huang
##   Packer Lab, York University
##
## For Windows. Not guaranteed to work on other platforms.

# Dev Notes
#   w = Widget(..).place(..) sets w to None. To avoid, separate them
#   Make list scroll with arrow keys
#
#   Timer method of validating
#     def check(self): dostuff, self.after(100, self.check)
#     then add app.after_idle(app.dostuff) before app.mainloop()
#
# Bugs
#   Problems with validating settings inputs
#     Restricting to #s works fine
#     Restricting to range sort of works but I need to find a way to do it after
#       any input without using a timer
#   Selecting part of an Entry and then typing inserts instead of replacing
#     Basically they don't work as neatly as I would like
#   Scrolling the list works but only as a bind_all
#
# Hotkeys
#   Ctrl+A to select all files+analyses
#   Ctrl+C to copy selected files+analyses to clipboard as tsv
#   Ctrl+V to paste selected files to list
#   Ctrl+S to save the current analysis (if complete)
#   Change settings by up/down, wheel
#   Navigate list by pg up/down, home/end, wheel, all arrows
#
# Quality of Life
#   Analysis should be done in a separate thread to allow pausing
#   Time the analysis and show with % in title bar
#   Right click files in the list
#     Open File Location
#     Trim Video (skips if already done)
#     Analyze
#   Clicking Start opens the Save dialog immediately, just to select location
#   Save Analysis, if only one file done or they have a common prefix, will have
#     a default name of Prefix
#   Save Analysis will always append _Sx_Ty_DD-MM-YYYY by default (user can just
#     erase this if they don't want it)
#   Closing the program or stopping a run will write "Cancelled" in the interval
#     column for files that were not analyzed
#   Ctrl +/- & 0 for resizing list text
#
# Safety
#   0 < Max Load
#   0 < Motion Sensitivity < 100
#   0 < Motion Threshold
#   Limit MaxLoad to a fraction of system RAM (0.6)
#     Or try to make it streaming


from Tkinter import *
from CallTipWindow import Tooltip
from CallTipWindow import createTooltip as hover
from VidHandler import *
from Motion import *

class App(Tk):
    # #################################
    #   GUI
    # #################################
    
    def __init__(self, parent=None):
        Tk.__init__(self, parent)
        self.parent = parent
        
        self.os_mw_c = 120 # 120 for Windows and Unix, -1 on OSX
        
        # Main menu bar
        self.mbar = Menu(self)
        
        # Construct the File menu
        self.mfile = Menu(self.mbar, tearoff=0)
        self.mfile.add_command(label="Add Videos", command="")
        self.mfile.add_command(label="Save Analysis As", command="")
        self.mfile.add_separator()
        self.mfile.add_command(label="Exit", command=self.destroy)
        
        # Construct the Help menu
        self.mhelp = Menu(self.mbar, tearoff=0)
        self.mhelp.add_command(label="Settings", command="")
        
        # Construct the About menu
        self.mabout = Menu(self.mbar, tearoff=0)
        self.mabout.add_command(label="Packer Lab", command="")
        self.mabout.add_command(label="[PROGRAM NAME]", command="")
        self.mabout.add_command(label="Program Version", command="")
        
        # Add these to the main menu
        self.mbar.add_cascade(label="File", menu=self.mfile)
        self.mbar.add_cascade(label="Help", menu=self.mhelp)
        
        # Add the main menu to the grid
        # Should stick to top left if window is resized
        self['menu'] = self.mbar
        
        # File list
        lfx = 15
        lfy = 15
        lfw = 500
        lfh = 384
        lfd = 14
        self.lfiles = Listbox(self, height=15, selectmode=EXTENDED, width=60)
        self.lfile_s = Scrollbar(self, orient=VERTICAL, command=self.OnScroll)
        self.lfile_s.place(x=lfx+lfw+lfd,y=lfy,width=4,height=lfh)
        self.lfiles['yscrollcommand'] = self.lfile_s.set
        self.lfiles.bind("<MouseWheel>", self.OnMouseWheel)
        
        for f in range(1,30):
            self.lfiles.insert(END, "Test List Item Number "+(str(f*5)*f*10))
        self.lfiles.place(x=lfx,y=lfy,width=lfw,height=lfh)
        
        # Placement deltas for the sidebar
        stx = 550
        stw_i = 100
        stdx = 105
        stw = 45
        stdx_u = 150
        stw_u = 75
        
        stdy = 30
        sty = 45
        
        # Settings containers - use .get() to access
        self.S_MaxLoad = StringVar()
        self.S_MaxLoad.set("200")
        self.S_MoSens = StringVar()
        self.S_MoSens.set("5")
        self.S_MoThres = StringVar()
        self.S_MoThres.set("5")
        
        # Validation init: restrict certain inputs to numbers only
        vali = (self.register(self.valn),'%d','%i','%P','%s','%S','%v','%V','%W')
        
        # Settings Header
        self.shead = Label(self,text="Settings")
        self.shead.place(x=stx,y=15,width=240,height=20)
        self.shead1 = Label(self,text="Mouse over for details")
        self.shead1.place(x=stx,y=35,width=240,height=20)
        
        # Setting: Max Load
        self.smload = Entry(self,width=10,exportselection=0,textvariable=self.S_MaxLoad,
                            validate='key', validatecommand=vali)
        self.smload.bind('<Key>', self.checkMaxLoad)
        self.smload.place(x=stx+stdx,y=sty+stdy,width=stw,height=20)
        self.smload_i = Label(self,text="Max Load",anchor=E)
        self.smload_i.place(x=stx,y=sty+stdy,width=stw_i,height=20)
        self.smload_u = Label(self,text="MB",anchor=W)
        self.smload_u.place(x=stx+stdx_u,y=sty+stdy,width=stw_u,height=20)
        hover(self.smload_i,"The maximum amount of data this program can load at any given time.")
        hover(self.smload,"Please keep this number well within your system's available RAM.")
        hover(self.smload_u,"Megabytes")
        
        # Setting: Motion Sensitivity
        self.smsens = Entry(self,width=10,exportselection=0,textvariable=self.S_MoSens,
                            validate='key', validatecommand=vali)
        self.smsens.bind('<Key>', self.checkMoSens)
        self.smsens.place(x=stx+stdx,y=sty+stdy*2,width=stw,height=20)
        self.smsens_i = Label(self,text="Motion Sensitivity",anchor=E)
        self.smsens_i.place(x=stx,y=sty+stdy*2,width=stw_i,height=20)
        self.smsens_u = Label(self,text="% Difference",anchor=W)
        self.smsens_u.place(x=stx+stdx_u,y=sty+stdy*2,width=stw_u,height=20)
        hover(self.smsens_i,"The minimum difference between frame to detect motion.")
        hover(self.smsens,"0 < x < 100")
        
        # Setting: Motion Threshold
        self.smthre = Entry(self,width=10,exportselection=0,textvariable=self.S_MoThres,
                            validate='key', validatecommand=vali)
        self.smthre.place(x=stx+stdx,y=sty+stdy*3,width=stw,height=20)
        self.smthre_i = Label(self,text="Interval Threshold",anchor=E)
        self.smthre_i.place(x=stx,y=sty+stdy*3,width=stw_i,height=20)
        self.smthre_u = Label(self,text="Seconds",anchor=W)
        self.smthre_u.place(x=stx+stdx_u,y=sty+stdy*3,width=stw_u,height=20)
        hover(self.smthre_i,"When no motion has been detected for this amount of time, the current motion interval ends.")
        hover(self.smthre,"Recommended 5 seconds or less")
        
        # Setting: Trim Video
        self.S_TrimVid = 0
        self.strimv = Checkbutton(self,variable=self.S_TrimVid)
        self.strimv.place(x=stx+stdx+11,y=sty+stdy*4)
        self.strimv_i = Label(self,text="Trim Videos",anchor=E)
        self.strimv_i.place(x=stx,y=sty+stdy*4,width=stw_i,height=20)
        hover(self.strimv_i,"When motion analysis is complete, a copy of the video will be created with motionless intervals replaced by a short blank sequence.")
        
        # Start button
        self.bstart = Button(self,text="Start Analysis",command=self.analyze,anchor=CENTER)
        self.bstart.place(x=stx+80,y=sty+stdy*6,width=80,height=50)
        
        ## For testing purposes
        self.btest = Button(self,text="Test",command=lambda:self.hello(t="Test"),anchor=CENTER)
        self.btest.place(x=600,y=350,width=40,height=20)
        
        # Input binding
        self.bind_all('<MouseWheel>', self.OnMouseWheel)
        
    # Validate inputs to the settings entries, restricting them to numbers only
    def valn(self, action, index, value_if_allowed, prior_value, text, 
             validation_type, trigger_type, widget_name):
        if text in '0123456789.':
            try:
                float(value_if_allowed)
                return True
            except ValueError:
                return False
        else:
            return False
        
    # Confirm that MaxLoad is set to a reasonable value (not negative!)
    ## LIMIT IT TO A FRACTION OF SYSTEM MEMORY
    def checkMaxLoad(self, *args):
        if float(self.S_MaxLoad.get()) > 100000:
            self.S_MaxLoad.set("100000")
            self.smload.focus()
            
    # Check that MoSens is set to a reasonable value (0 < ms < 100)
    def checkMoSens(self, *args):
        if float(self.S_MoSens.get()) > 100.0:
            self.S_MoSens.set("100.0")
            self.smsens.focus()
            
    # #################################
    #   Additional Input Handling
    # #################################
    
    def OnMouseWheel(self, event):
        ## Problem is with this condition. focus isn't set at all???
        print self.focus_get()
        if self.focus_get() == self.lfiles or self.focus_get() == self.lfile_s:
            self.lfiles.yview("scroll", -1*(event.delta/self.os_mw_c), "units")
            return "break"
    
    def OnMouseClick(self, event):
        pass
    
    def OnKey(self, event):
        pass
    
    def OnScroll(self, *args):
        self.lfiles.yview(*args)
    
    # Show a popup window. Will be used to test whether code has been called at all
    # Also serves as an example of how to make extra popups
    # Call using   self.hello(t="")
    def hello(self, t, *args):
        toplevel = Toplevel()
        hello = Label(toplevel, text=t)
        hello.pack()
        toplevel.focus_force()

    # #################################
    #   Motion
    # #################################

    def analyze(self):
        # Change button text and command to allow pausing
        self.smload.config(state=DISABLED)
        self.smsens.config(state=DISABLED)
        self.smthre.config(state=DISABLED)
        self.strimv.config(state=DISABLED)
        self.bstart.config(text="Stop Analysis",command=self.analyze_stop)
    
    def analyze_stop(self):
        # Reset button text and command
        self.smload.config(state=NORMAL)
        self.smsens.config(state=NORMAL)
        self.smthre.config(state=NORMAL)
        self.strimv.config(state=NORMAL)
        self.bstart.config(text="Start Analysis",command=self.analyze)

# #################################
#   Main
# #################################

if __name__ == "__main__":
    app = App()
    app.title("VRex v0.x")
    app.geometry("800x420")
    app.resizable(0,0)
    app.mainloop()

