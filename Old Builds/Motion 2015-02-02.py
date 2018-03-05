# Things to do when porting to proper directory
# http://opencv-python-tutroals.readthedocs.org/en/latest/py_tutorials/py_video/py_lucas_kanade/py_lucas_kanade.html
# https://pragprog.com/magazines/2012-05/what-makes-an-awesome-commandline-application
# http://www.diveintopython.net/object_oriented_framework/defining_classes.html

build = "2015-02-02"

import os, sys, platform, time, datetime
sys.path.append(os.getcwd()+'//Lib')
sys.path.append(os.getcwd()+'//Lib//site-packages')
import cv2, numpy
from MMisc import *
#from MMisc import rn, fr2s, fr2t, fr2ts, s2t, abbv, isint, isvid, get_ext

# bvid structure
# 0 Video link (valid path, as a string)
# 1 VideoCapture object
# 2 Metadata [W(px), H(px), FPS, time(s), frames]
# 3 Status "N", "Y"

class MotionTester:    
    def __init__(self):
        self.CMDL_GO = False    # Take command-line input?
        self.OW = False         # Overwrite already-processed videos in bin?
        self.MODE = 1           # Method of motion detection, 1 = difference threshold
        self.LOGFRQ = 5.0       # Log progress every LOGFRQ minutes
        
        self.vbin = []          # Video bin, stores links and interval data
        self.outf = None        # Output file for interval data
        self.mklog()            # Create a log file for each session
        
        self.itv_minlen = 0.5   # Motion must be detected for N s to declare an interval
        self.itv_frbuff = 15    # N frames can pass without motion before an interval ends
        self.itv_mergethr = 2   # Intervals less than N seconds apart will be merged
        
        self.dt_mindif = 0.00015     # Minimum proportion of difference for motion
        self.dt_maxdif = 0.005     # Maximum proportion of difference for motion
        
        #self.lk_setting = x
        
    #==== Core Operations ====================
    
    ## Close logfile and pending output files and allow the main loop to end, if applicable
    def leave(self):
        self.logf.close()
        # close output files
        # close videos
        self.CMDL_GO = False
        print "> Goodbye!"
    
    ## Create a log file specific to this session
    def mklog(self):
        self.logf = open("Motion Log "+str(datetime.datetime.now()).replace(":",".")+".txt", "w")
        self.logf.write("==== Motion Log "+str(datetime.datetime.now())+" ====\n"+build+" build | Python v"+platform.python_version()+" | OpenCV v"+cv2.__version__)
    
    ## Write a message to both the console and logfile
    def log(self, st):
        print st
        self.logf.write("\n"+st)
    
    ## Check whether a given index (pos - 1) would be valid for the current video bin  
    def posinbin(self, pos):
        if len(self.vbin) == 0:
            return False
        elif pos-1 < 0 or pos > len(self.vbin):
            return False
        else:
            return True
    
    ## Add a video to the video bin and check video properties
    def addvid(self, link, chk=False, re=False):
        if os.path.isdir(link):
            for filename in os.listdir(link):
                if isvid(get_ext(filename)):
                    self.addvid(os.path.join(link,filename))
        else:
            vid = cv2.VideoCapture(link)
            if vid.isOpened():
                metadata = [-1, -1, 0, "", 0]
                metadata[0] = int(vid.get(cv2.cv.CV_CAP_PROP_FRAME_WIDTH))
                metadata[1] = int(vid.get(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT))
                metadata[2] = int(vid.get(cv2.cv.CV_CAP_PROP_FPS))
                metadata[4] = int(vid.get(cv2.cv.CV_CAP_PROP_FRAME_COUNT))
                metadata[3] = fr2ts(metadata[4], metadata[2])
                self.vbin.append([os.path.abspath(link), vid, metadata, "N", []])
                if not chk:
                    self.log("  > Added video "+link)
                    self.log("    > Properties: "+str(metadata[0])+"x"+str(metadata[1])+", "+str(metadata[2])+" FPS, "+metadata[3]+" ("+str(metadata[4])+" frames)")
                else:
                    self.log("  > Confirmed that video "+link+" has not changed since being added to the bin")
            else:
                if not chk: 
                    self.log("  > Warning: addvid("+link+") failed: No compatible video could be found.")
                else:
                    self.log("  > Warning: chkvid("+link+"): Video has changed since added to the bin")
    
    #def readdvid(self, link):
        #vid = cv2.VideoCapture(link)
        #if vid.isOpened():
            #metadata = [-1, -1, 0, "", 0]
            #metadata[0] = int(vid.get(cv2.cv.CV_CAP_PROP_FRAME_WIDTH))
            #metadata[1] = int(vid.get(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT))
            #metadata[2] = int(vid.get(cv2.cv.CV_CAP_PROP_FPS))
            #metadata[4] = int(vid.get(cv2.cv.CV_CAP_PROP_FRAME_COUNT))
            #metadata[3] = fr2t(metadata[4], metadata[2])
            #return [link, vid, metadata, "N", []]
        #else:
            #self.log("  > Warning: readdvid("+link+"): Video could not be found")
            #return None
    
    ### Check that a target video (path) matches a video already in the bin
    ### Used at the start of a runvid to confirm that the video has not changed since addvid
    ### Uses metadata because the runvid call will already have access to the bin data
    #def chkvid(self, metadata, path):
        #vbinlen = len(self.vbin)
        #self.addvid(path, chk=True)
        #if len(self.vbin) > vbinlen:
            #self.remvid(-1, log=False)
            #if metadata == self.vbin[len(self.vbin)-1][2]:
                #return True
            #else:
                #self.log("  > Warning: chkvid("+path+"): video has changed since being added to the video bin")
                #return False
        #else:
            #self.log("  > Warning: chkvid("+path+") failed: the video no longer exists or has been renamed, or an invalid path was given")
            #return False
    
    ## Remove the video at a particular position in the video bin.
    def remvid(self, pos, log=True):
        if pos == -1: # Remove the last video in the bin
            gone = self.vbin.pop(len(self.vbin)-1)
            if log:
                self.log("  > Video "+gone[0]+" was removed from the bin.")
        elif not self.posinbin(pos):
            self.log("  > Warning: remvid("+str(pos)+") failed, vbin index out of bounds.")
        else:
            self.log("  > Video "+self.vbin.pop(pos-1)[0]+" was removed from the bin.")
    
    ## Return the VideoCapture of a video in the bin at a given position
    def getvid(self, pos):
        if not self.posinbin(pos):
            self.log("  > Warning: getvid("+str(pos)+") failed, vbin index out of bounds.")
        else:
            return self.vbin[pos-1][1]
    
    ## Return the index of a video in the bin matching a filename or path
    def findvid(self, key):
        hits = [i for i, v in enumerate(self.vbin) if key in v[0]]
        if len(hits) > 1:
            self.log("  > Warning: findvid("+key+") found more than 1 matching video.")
            self.log("    > Passing -2 to the next function, which will cause it to fail.")
            return -2
        elif len(hits) == 0:
            self.log("  > Warning: findvid("+key+") found no matching videos.")
            self.log("    > Passing -1 to the next function, which will cause it to fail.")
            return -1
        else:
            return hits[0]
    
    def changemode(self, n):
        if n in (1, 2):
            self.mode = n
        else:
            self.log("  > Warning: changemode("+str(n)+") failed, input must be 1 or 2")
            #raise DataError("changemode("+n+"): invalid input, must be 1 or 2")
    
    ## General function to call anytime a user wants a run.
    ## This will run a more specific run function based on the current mode.
    def runvid(self, pos):
        if not self.posinbin(pos):
            self.log("  > Warning: runvid("+str(pos)+") failed, vbin index out of bounds")
        elif self.vbin[pos-1][3] == "Y" and self.OW == False:
            self.log("  > Skipped run of "+self.vbin[pos-1][0]+" due to existing motion data.")
        else:
            ati = time.time()
            mti = time.clock()
            self.log("  > Beginning motion analysis of "+self.vbin[pos-1][0])
            self.log("    > Intervals can have at most "+str(self.itv_frbuff)+" consecutive motionless frames")
            self.log("    > Intervals less than "+str(self.itv_mergethr)+" s apart will be merged")
            self.log("    > Intervals less than "+str(self.itv_minlen)+" s long will be omitted")
            # reset videocapture's position in the video somehow!
            self.vbin[pos-1][3] = "N"
            self.vbin[pos-1][4] = []
            
            ### Check that the video has not changed since being added
            #valid = self.chkvid(self.vbin[pos-1][2], self.vbin[pos-1][0])
            #if not valid:
                #self.log("  > Warning: runvid("+self.vbin[pos-1][0]+"): video has changed since being added to the bin. Re-reading video data before continuing to run.")
                #self.vbin[pos-1] = self.readdvid(self.vbin[pos-1][0])
                #if self.vbin[pos-1] is None:
                    #self.log("  > Error: Cancelled rerun as the video could not be found")
                    #return
                
            ## Finally, run the video
            if self.MODE == 1:
                self.run_dt(self.vbin[pos-1])
            elif self.MODE == 2:
                self.run_lk(self.vbin[pos-1])
                
            ## Consolidate intervals
            # self.itv_mergethr - in s; bvid[2][2] = fps
            for i, bvid in enumerate(self.vbin):
                citv = len(bvid[4])
                nitvs = []
                nitv = [0, 0]
                for itv in bvid[4]:
                    if nitv[0] == 0:
                        nitv = list(itv)
                    else:
                        if itv[0] - nitv[1] < self.itv_mergethr*bvid[2][2]:
                            nitv[1] = int(itv[0])
                        else:
                            nitvs.append(list(nitv))
                            nitv = [0, 0]
                if len(bvid[4]) > 0:
                    bvid[4] = list(nitvs)
                    self.log("    > Condensed "+str(citv)+" intervals to "+str(len(bvid[4])))
            
            ## Keep interval data as frames. Convert to time only during output()
            atf = time.time()
            mtf = time.clock()
            self.log("    > Completed analysis of "+os.path.basename(self.vbin[pos-1][0])+" in "+str(rn(mtf-mti))+" process seconds ("+s2ts(mtf-mti)+")")
            if rn(mtf-mti) - rn(atf-ati) > 0.01:
                self.log("      > Actual time taken estimated at "+str(rn(atf-ati))+" seconds ("+s2ts(atf-ati)+")")
            self.vbin[pos-1][3] = "Y"
        # update bin status in the run function
    
    def run_lk(self, bvid):
        # Analyze using Lucas-Kanade optical flow as described at
        # http://opencv-python-tutroals.readthedocs.org/en/latest/py_tutorials/py_video/py_lucas_kanade/py_lucas_kanade.html
        self.log("    > Lucas-Kanade optical flow analysis for "+str(vid))
        self.log("      > Settings: ")
        # self.itv_minlen * bvid[2][2], self.itv_frbuff, self.itv_mergethr * bvid[2][2]
        # bvid[x] = [path, VideoCapture, metadata[], "Y/N", []]
        # bvid[2] = [W, H, FPS, len(time), len(frames)]
        #self.itv_minlen = 0.1   # Motion must be detected for N s to declare an interval
        #self.itv_frbuff = 5     # N frames can pass without motion before an interval ends
        #self.itv_mergethr = 2   # Intervals less than N seconds apart will be merged
        
    # http://www.steinm.com/blog/motion-detection-webcam-python-opencv-differential-images/
    def run_dt(self, bvid):
        ## Analyze using difference threshold - crudest method
        ## All position numbers are frames, not time
        self.log("    > Difference threshold analysis for "+bvid[0])
        self.log("      > Differences between "+str(rn(self.dt_mindif*100.0))+"%-"+str(rn(self.dt_maxdif*100.0))+"% will be detected.")
        
        res = bvid[2][0]*bvid[2][1]        
        itv_active = False
        itv = [0, 0]
        motion = False
        fr = 0
        fr_buffer = self.itv_frbuff
        frs = [None, None, None]
            
        while bvid[1].isOpened():
            ## Populate the frame trio
            if None in frs:
                for i in (0, 1, 2):
                    if frs[i] is None:
                        frs[i] = cv2.cvtColor(bvid[1].read()[1], cv2.COLOR_RGB2GRAY)
                        fr += 1
            else:
                ## Transform the current set of frames to find total contrast
                img_diff = cv2.bitwise_and(cv2.absdiff(frs[2],frs[1]),cv2.absdiff(frs[1],frs[0]))
                img_thre = cv2.threshold(img_diff, thresh=10.0, maxval=255.0, type=cv2.THRESH_BINARY)
                img_cont = cv2.countNonZero(img_thre[1])
                
                ## Check if the current set of frames has motion
                motion = True if img_cont >= self.dt_mindif*res and img_cont < self.dt_maxdif*res else False
                
                ## Advance intervals if needed
                ## Wait at most self.itv_frbuff motionless frames before ending an interval
                if itv_active:
                    if motion:
                        fr_buffer = self.itv_frbuff
                    else:
                        fr_buffer -= 1
                        if fr_buffer <= 0:
                            itv_active = False
                            itv[1] = fr - self.itv_frbuff
                            if itv[1] - itv[0] >= self.itv_minlen*bvid[2][2]:
                                bvid[4].append(list(itv))
                else:
                    if motion:
                        itv_active = True
                        itv[0] = fr
                        fr_buffer = self.itv_frbuff
                        
                ## Give a progress report every 60 s
                if fr % (bvid[2][2]*60*self.LOGFRQ) == 0:
                    self.log("      > At frame "+str(fr)+" ("+fr2ts(fr,bvid[2][2])+"), "+str(len(bvid[4]))+" raw intervals found")
                
                ## Move to the next frame set
                fr += 1
                notdone, nextfr = bvid[1].read()
                if notdone:
                    frs[0] = frs[1]
                    frs[1] = frs[2]
                    frs[2] = cv2.cvtColor(nextfr, cv2.COLOR_RGB2GRAY)
                else:
                    if itv_active:
                        itv[1] = fr - self.itv_frbuff
                        if itv[1] - itv[0] >= self.itv_minlen*bvid[2][2]:
                            bvid[4].append(list(itv))
                    break
        self.log("    > Reached end of video with "+str(len(bvid[4]))+" intervals found.")
    
    #==== UI Operations ====================
    def showbin(self):
        if len(self.vbin) == 0:
            print "  > No videos loaded."
        else:
            print "  > Motion Video Bin as of "+str(datetime.datetime.now())
            print '%4s %-32s %5s  %5s  %3s  %11s %7s %4s' % ("#", "             Video Path", "W", "H", "FPS", "Length", "Frames", "Done")
            for i, v in enumerate(self.vbin):
                print '%4i %-32s %5i %5i  %3i  %11s %7i %4s' % (i+1, abbv(v[0],32), v[2][0], v[2][1], v[2][2], v[2][3], v[2][4], v[3])
    
    def showmode(self):
        if self.MODE == 1:
            return "Difference Threshold"
        elif self.MODE == 2:
            return "Lucas-Kanade Optical Flow"
        else:
            return "Unknown"
        
    def output(self, outfn):
        # See tkFileDialog.asksaveasfilename()
        if len([True for bvid in self.vbin if len(bvid) >= 4 and bvid[3] == "Y"]) > 0:
            strs = []
            strs.append("\n=============== MOTION ANALYSIS RESULTS ===============")
            for i, vid in enumerate(self.vbin):
                strs.append("\nVideo "+str(i+1)+": "+os.path.abspath(vid[0]))
                strs.append("  Properties: "+str(vid[2][0])+"x"+str(vid[2][1])+", "+str(vid[2][2])+" FPS, length "+vid[2][3])
                if len(vid[4]) > 0:
                    strs.append("  Motion Intervals Found:")
                    for i, itv in enumerate(vid[4]):
                        strs.append("    "+str(i+1)+"\t"+fr2ts(itv[0],vid[2][2])+"-"+fr2ts(itv[1],vid[2][2])+" ("+df2t(itv[0],itv[1],vid[2][2])+")")
                elif vid[3] == "Y":
                    strs.append("  No motion found within parameters.")
                else:
                    strs.append("  No motion analysis done at the time of writing.")
                    
            if outfn == "Motion_SaveToCurrentSessionLogFile_UsingStringUsersShouldNotEverCoincidentallyUseAsFileName":
                for ln in strs:
                    self.log(ln)
            else:
                try:
                    ## check if path is valid and is not overwriting something
                    ## if is overwriting, append something (check that too)
                    outf = open(outfn, "w")
                    for ln in strs:
                        outf.write(ln)
                except Exception as e:
                    print "  > Error while trying to save video analysis data."
                    print "    > Showing error details below:"
                    print "      "+repr(e)
                    print "    > Your data has not been lost. You can try saving again."
                    print "    > If all else fails, use save without a parameter to save to the logfile."
        else:
            print "  > There is no video analysis data to save."
        
        # bvid[Link,VideoCapture,Metadata[W,H,FPS,t(s),f],Status,Intervals]
    
    def runcmd(self, cmd):
        if cmd.find(" ") > -1:
            key, args = cmd.split(" ", 1)
            if key == "exit":
                print "  > The exit command does not take parameters. Omit those next time."
                self.leave()
            elif key == "help":
                print "  > The help command does not take parameters. Omit those next time."
                commands()
            elif key == "ow":
                if args.lower() in ('0', 'n', 'f', 'off'):
                    self.OW == False
                    print "  > Motion will no longer redo already-analyzed videos when a run is called."
                elif args.lower() in ('1', 'y', 't', 'on'):
                    self.OW == True
                    print "  > Motion will now redo already-analyzed videos when a run is called."
                else:
                    print "  > Parameters '"+args+"' for command ow not recognized."
                    print "    > Hint: You can use ow 1/0, ow y/n, ow t/f, ow on/off or just ow"
            elif key == "save":
                pass # ############
            elif key == "bin":
                print "  > The bin command does not take parameters. Omit those next time."
                self.showbin()
            elif key == "mode":
                if args in ('1', '2'):
                    self.MODE = int(args)
                    print "  > Changed motion detection method to "+self.showmode()+"."
                else:
                    print "  > Received an invalid parameter for the mode command."
                    print "    > The correct usage is mode <N>"
                    print "      mode 1 for Difference Threshold, the crudest method."
                    print "      mode 2 for Lucas-Kanade Optical Flow."
            elif key in ('add', 'rem', 'run'):
                # Handle run all, then run <N>/rem <N>, then bad paths, then normal run <Path>
                if key == "run" and args == "all":
                    if len(self.vbin) > 0:
                        print "  > Running all "+str(len(self.vbin))+" videos currently in the bin."
                        print "    > OW = "+str(self.OW)+": videos already completed will "+("not " if not self.OW else "")+"be redone."
                        for i, v in enumerate(self.vbin):
                            self.runvid(i+1)
                    else:
                        print "  > There are no videos to run!"
                elif key in ('run', 'rem') and isint(args):
                    if key == "run":
                        self.runvid(int(args))
                    else:
                        self.remvid(int(args))
                elif not os.path.exists(args) and not os.path.exists(os.getcwd()+"/"+args):
                    print "  > Warning: "+key+" failed due to '"+args+"' not being a valid or existing file or directory path."
                else:
                    if key == "run":
                        self.runvid(args)
                    elif key == "rem":
                        self.remvid(self.findvid(args))
                    elif key == "add":
                        self.addvid(args)
            else:
                print "  > Command not recognized. Type help for a list of valid commands."
        else:
            if cmd == "exit":
                self.leave()
            elif cmd == "help":
                MotionTester.commands()
            elif cmd == "ow":
                if self.OW == True:
                    self.OW == False
                    print "  > Motion will no longer redo already-analyzed videos when a run is called."
                else:
                    self.OW == True
                    print "  > Motion will now redo already-analyzed videos when a run is called."
            elif cmd == "save":
                self.output("Motion_SaveToCurrentSessionLogFile_UsingStringUsersShouldNotEverCoincidentallyUseAsFileName")
            elif cmd == "add":
                print "  > Usage:    add <PathToVideoFile>"
                print "    > Use the full path (e.g. add C:/Users/User/Documents/Videos/vid.avi) if your"
                print "      video is located somewhere other than this program's folder. Otherwise, you"
                print "      can use the relative path (e.g. add vid.avi)."
            elif cmd == "rem":
                print "  > Usage:    rem <PathToVideoFile>"
                print "          or  rem <VideoFileName>"
                print "          or  rem <VideoPositionInBin>     (an integer)"
                print "    > The full path to the video file will always remove the specified video from"
                print "      the bin. The video file name will only remove the video if the bin does not"
                print "      contain other videos having the same name. Use the bin command to find each"
                print "      video's numerical position in the bin."
            elif cmd == "bin":
                self.showbin()
            elif cmd == "mode":
                print "  > Current motion detection method is "+self.showmode()+"."
                print "    > To change this, use the command mode <N>"
                print "      mode 1 for Difference Threshold, the crudest method."
                print "      mode 2 for Lucas-Kanade Optical Flow."
            elif cmd == "run":
                print "  > Usage:    run <PathToVideoFile>"
                print "          or  run <VideoFileName>"
                print "          or  run <VideoPositionInBin>"
                print "          or  run all"
                print "    > Select and run a video in the current video bin using the full path for the"
                print "      video, the video's file name (if there are other videos with the same name,"
                print "      this will fail) or the video's position in the bin which can be viewed with"
                print "      the bin command. For a path or filename, if the bin does not contain a file"
                print "      that matches, Motion will attempt to use the add command first."
                print "    > Alternatively, use run all to run every video in the current video bin."
                print "    > Videos that already have motion data will be skipped in all subsequent runs"
                print "      unless the OW setting is set to On. Use the mode command to change this."
            else:
                print "  > Command not recognized. Type help for a list of valid commands."
                
    @staticmethod    
    def commands():
        print "  > help           Shows this list of commands."
        print "  > exit           Exit the program and save any pending output files."
        print "  > add <Path>     Adds the video (or videos in the folder) to the video bin."
        print "  > rem <Path>     Removes all matching videos from the video bin."
        print "  > bin            Shows the current video bin."
        print "  > run <N>        Analyzes the video at position N in the video bin."
        print "  > run <Path>     Analyzes all matching videos and adds them to the video bin."
        print "  > run all        Analyzes all videos currently in the video bin."
        print "  > ow             Toggle whether to redo when running videos."
        print "  > mode <N>       Change the method of motion detection."
        print "                     1 = Difference Threshold (crudest)"
        print "                     2 = Lucas-Kanade Optical Flow"
        print "  > save           Save interval data for the video bin in the current logfile."
        print "  > save <Path>    Save interval data for the video bin in the specified location."
        print
        print "  > <N> is any integer greater than 0. Not all such numbers are accepted."
        print "  > Video properties are checked when videos are added to the bin. Videos are not"
        print "    actually loaded until a run is called."
        
#==== Main ====================
if __name__ == "__main__":
    print "-"*64
    print "|      MOTION      |   by Jonathan Huang   |   Python v"+platform.python_version()+"   |"
    print "| "+build+" build |   YorkU: Packer Lab   |   OpenCV v"+cv2.__version__+"   | "
    print "-"*64
    print "> Type help for a list of commands."
    M = MotionTester()
    M.CMDL_GO = True
    while M.CMDL_GO:
        M.runcmd(raw_input("\n>>> "))

#add samples/Bahar.Aug5.13b.mp4
#add samples/Bahar.July27.13b.mp4
#add samples/CSEE.08.30.13.1.mp4
#add samples/Danby. Aug 8.13c.mp4