## Command-line access to VidHandler and motion analysis

import os, sys, platform, time, datetime
sys.path.append(os.getcwd()+'\\Lib')
sys.path.append(os.getcwd()+'\\Lib\\site-packages')
import VidHandler
import cv2
import numpy

DATE = datetime.datetime.now()
LOG = open("motion_log_"+str(DATE.year)+"-"+str(DATE.month)+"-"+str(DATE.day)
           +"_t"+str(DATE.hour)+"h"+str(DATE.minute)+"m.txt","w")
CONTINUE = True

mothre = 0.1    # Minimum interval length
mobuff = 5      # Frames to wait until declaring an interval over
merthr = 2      # Maximum seconds between intervals to be merged

MODE_THRES_DIFF = 1
mosens = 1.5e-4 # Minimum difference between frames that implies motion
mostop = 0.0025 # Maximum difference; avoids whole-frame actions being detected

mode = MODE_THRES_DIFF

fname = ""  # Name of input file
f = None    # VideoCapture object
meta = []   # Video metadata [Width in px, Height in px, FPS, Frames, Length in s]
itvf = []   # Motion intervals (start_frame, end_frame)
itvs = []   # Motion intervals (start_time, end_time) in HH:MM:SS (round to last s)
outf = open("motion test.txt", "w")

##========== MAIN ==============================================================
# Prints a list of commands
def help():
    print
    print ">> STANDALONE COMMANDS"
    print "   >> help         --- Shows this list of commands."
    print "   >> exit         --- Exits the program."
    print "   >> mode X       --- Sets the mode of motion detection."
    print "                       1 = difference threshold (in % of pixels)"
    print "                       2 = object detection based"
    print
    print ">> VIDEO COMMANDS"
    print "   >> read X       --- Attempts to read the selected video file."
    print "                       Note: Full path needed. No quotes needed."
    print "   >> show X       --- Reads and plays the selected video file."
    print "   >> show         --- Plays the currently loaded video file."
    print "   >> analyze      --- Starts motion analysis for the current video"
    print "                       file using current settings."
    print

# Gets input and takes action accordingly
def getinput():
    global fname, f, meta
    print
    inp = raw_input(">> Command: ")
    print
    sp = inp.find(" ")
    
    if sp == -1:
        if inp == "help":
            help()
        elif inp == "exit":
            close()
        elif inp == "show":
            if f.isOpened():
                showvideo()
            else:
                print ">> ERROR: A video was not loaded."
                # What about a video that we hit the end of?
        elif inp == "analyze":
            if f.isOpened():
                analyze()
            else:
                print ">> ERROR: A video was not loaded."
    else:
        keyw = inp[:sp]
        if keyw == "read" or keyw == "show" or keyw == "analyze":
            fname = inp[len(keyw)+1:]
            getvideo()
        if keyw == "analyze":
            analyze()
        if keyw == "show":
            showvideo()
    
# Get a video and attempt to read it and get metadata. Assign to global variables.
def getvideo():
    global fname, f, meta
    f, meta = VidHandler.read(fname)
    if f is None or meta is None:
        print ">> ERROR: Could not read the video. Either your path is incorrect, or"
        print "   the file wasn't an uncompressed AVI. Support for more formats is a"
        print "   future goal but depends on installed codecs."
    else:
        meta = VidHandler.getMetadata(f)
        print ">> Successfully opened "+fname+"."
        print "   >> Properties: "+str(meta[0])+"x"+str(meta[1])+"px, "+str(meta[2])+" FPS, "+str(meta[3])+" frames, "+str(meta[4])+" s"

# Display the video currently loaded. Mainly for testing purposes.
# Note that while this is running, printing to console may pause.
def showvideo():    
    print ">> Viewing "+fname+" now."
    print "   >> Press Q to close the video frame."
    print
    while f.isOpened():
        notdone, frame = f.read()
        if notdone:
            cv2.imshow(fname, frame)
        else:
            print ">> Reached end of video."
            break
        if cv2.waitKey(10) & 0xFF == ord('q'):
            print ">> Exiting early."
            break
        time.sleep(1.0/meta[2])
    
    f.release()
    cv2.destroyAllWindows()
    
# Complete any pending tasks and exit the program.
def close():
    global CONTINUE
    print ">> Goodbye!"
    CONTINUE = False
    LOG.close() 

def log(st):
    print st
    LOG.write(st+"\n")

##========== EXTERNAL HANDLING==================================================

# Clear data variables in preparation for a new input + analysis
def reset():
    global fname, f, meta, itvs, outf
    fname = ""
    f = None
    meta = []
    itvs = []
    outf = None

def analyze():
    global f, fname, meta, itvf, itvs
    
    log(">> For "+fname)
    log("   >> "+str(meta[0])+"x"+str(meta[1])+", "+str(meta[2])+" FPS, "+
        str(meta[3])+" frames / "+str(datetime.timedelta(seconds=meta[4])))
    log("   >> Motion thresholds "+str(mosens*100)+"% min, "+str(mostop*100)+"% max")
    log("   >> Minimum interval length "+str(mothre)+" s, buffer of "+str(mobuff)+" frames")
    log("   >> Intervals less than "+str(merthr)+" s apart will be merged")
    log(">> Starting motion analysis")
    
    ati = time.time()
    mti = time.clock()
    
    # Do motion interval analysis
    # Uses differential image method, using 3 consecutive frames
    # http://www.steinm.com/blog/motion-detection-webcam-python-opencv-differential-images/
    ininterval = False
    interval = [0, 0]
    motion = False
    mbuffer = mobuff
    mthres = mosens*meta[0]*meta[1]
    mstop = mostop*meta[0]*meta[1]
    fi = 2
    t = [cv2.cvtColor(f.read()[1], cv2.COLOR_RGB2GRAY),
         cv2.cvtColor(f.read()[1], cv2.COLOR_RGB2GRAY),
         cv2.cvtColor(f.read()[1], cv2.COLOR_RGB2GRAY)]
    while f.isOpened():
        
        # Transform the current set of frames and get total contrast
        idiff = subtract(t[0], t[1], t[2])
        ithre = cv2.threshold(idiff, thresh=10.0, maxval=255.0, type=cv2.THRESH_BINARY)
        icntr = getcontrast(ithre[1])
        
        # Check if this frame qualifies as motion
        motion = True if icntr >= mthres and icntr < mstop else False
        
        # Should have a buffer of about 6 frames before NoMotion is called
        # Handle intervals
        if ininterval:
            if motion:
                mbuffer = mobuff
            else:
                mbuffer -= 1
                if mbuffer <= 0:
                    ininterval = False
                    interval[1] = fi - mobuff
                    if (interval[1] - interval[0]) >= meta[2]*mothre:
                        itvf.append(list(interval))
        else:
            if motion:
                ininterval = True
                interval[0] = fi
                mbuffer = mobuff
        
        # Move to the next frame        
        fi += 1
        notdone, tn = f.read()

        # Give a progress report every 60 s
        if fi % (meta[2]*60) == 0:
            log("   >> Progress report: now at "+str(fi/(meta[2]*60))+" m, "+str(len(itvf))+" intervals found.")
        
        if notdone: # move to next frame
            t[0] = t[1]
            t[1] = t[2]
            t[2] = cv2.cvtColor(tn, cv2.COLOR_RGB2GRAY)
        else: # end current interval
            if ininterval:
                interval[1] = fi - mobuff
                if (interval[1] - interval[0]) >= meta[2]*mothre:
                    itvf.append(list(interval))
            break
    
    #itvf = consolidate(itvf)
    convert_time()
    write()
    
    atf = time.time()
    mtf = time.clock()
    log(">> Completed analysis of "+fname+" in "+str(mtf-mti)+" process seconds")
    log(">> Actual time taken estimated at "+str(atf-ati)+" seconds")

## Test 1: 105 bee movements in/out
## analyze C:\Users\Ganzicus\Desktop\Packer Lab\motiond\samples\CSEE.08.30.13.1.mp4
## Test 2: no bees
## read C:\Users\Ganzicus\Desktop\Packer Lab\motiond\samples\Bahar.Aug5.13b.mp4

##========== IMAGE COMPARISON ==================================================
    
def subtract(im1, im2, im3):
    d1 = cv2.absdiff(im3, im2)
    d2 = cv2.absdiff(im2, im1)
    return cv2.bitwise_and(d1, d2)

def getcontrast(im):
    r = cv2.countNonZero(im)
    return r

##========== MOTION INTERVALS ==================================================

def consolidate(itvl):
    cont = False
    ito = []
    its = 0
    ite = 1
    thr = merthr*meta[2]
    log(">> Attempting to merge intervals less than "+str(merthr)+" seconds apart.")
    while True:
        if its >= len(itvl) or ite >= len(itvl): # Reached end of list
            break
        if itvl[its][0] - itvl[ite][1] <= thr: # Merge needed
            ite += 1
            while ite < len(itvl):
                if itvl[ite+1][0] - itvl[ite][1] <= thr: # continue
                    ite += 1
                else: # break out and add this interval
                    ito.append([itvl[its][0], itvl[ite][1]])
                    log("  >> Added merged interval "+str(if2m(ito[len(ito)-1])))
                    its = ite + 1
                    ite = its + 1
                    break
            if ite == len(itvl)-1: # Add final interval if applicable
                ito.append([itvl[its][0], itvl[ite][1]])
                log("  >> Added merged interval "+str(if2m(ito[len(ito)-1])))
        else: # No merge needed - continue through list
            its += 1
            ite += 1
    log(">> Consolidated to "+str(len(ito))+" intervals.")
    return ito

def convert_time():
    global itvs
    for itv in itvf:
        itvs.append([datetime.timedelta(seconds=itv[0]/meta[2]), datetime.timedelta(seconds=itv[1]/meta[2])])

##========== MISC FUNCTIONS ====================================================

def rn(n):
    return round(n, 2)

def f2s(f):
    return rn(f/meta[2])

def s2f(s):
    return int(s*meta[2])

def f2m(f):
    return rn(f/meta[2]/60.0)

def m2f(m):
    return int(m*60.0*meta[2])

def s2m(s):
    return rn(s/60.0)

def m2s(m):
    return rn(m*60.0)

def if2s(itv):
    return [f2s(itv[0]), f2s(itv[1])]

def if2m(itv):
    return [f2m(itv[0]), f2m(itv[1])]

def is2f(itv):
    return [s2f(itv[0]), s2f(itv[1])]

##========== OUTPUT ============================================================

def write():
    global itvs, outf
    outf.write(fname+"\n")
    outf.write("Video: "+str(meta[0])+"x"+str(meta[1])+", "+str(meta[2])+" FPS, "+
               str(meta[3])+" frames / "+str(datetime.timedelta(seconds=meta[4]))+"\n")
    outf.write("Motion thresholds "+str(mosens*100)+"% min, "+str(mostop*100)+"% max\n")
    outf.write("Minimum interval length "+str(mothre)+" s, buffer of "+str(mobuff)+" frames\n")
    for i, itv in enumerate(itvf):
        outf.write("I#"+str(i+1)+"\t| "+str(itvs[i][0])+" to "+str(itvs[i][1])+" ("+
                   str((itvs[i][1]-itvs[i][0]))+") | frames "+
                   str(itv[0])+" to "+str(itv[1])+" ("+str(itv[1]-itv[0])+")\n")
    outf.close()
    # ask to name file
    # ask to put in same directory or put direct path
    # check if file already exists
    # if so, confirm to overwrite or go back to start
    

##========== END ===============================================================

if __name__ == "__main__":
    print "+----------+-------------------+-------------------+"
    print "|  MOTION  | by Jonathan Huang | YorkU: Packer Lab |"
    print "|----------+-------+-----------+---+---------------|" 
    print "| 08/26/2014 build | Python v"+platform.python_version()+" | OpenCV v"+cv2.__version__+" | "
    print "+------------------+---------------+---------------+" 
    print ">> Type help for a list of commands."
    while CONTINUE:
        getinput()