## Miscellaneous functions and exceptions used in Motion
import datetime

## Round a number to 2 decimal places
def rn(n):
    return round(n, 2)

## Calculate the time difference between two times in the str format "HH:MM:SS.MS"
def dt(t1, t2):
    tf = "%H:%M:%S.%f"
    return datetime.datetime.strptime(t2, tf) - datetime.datetime.strptime(t1, tf)

## Calculate the time difference between two frame positions
def df2t(t1, t2, fps):
    return fr2ts(t2-t1, fps)

## Convert frames to seconds
def fr2s(fr, fps):
    return fr*1.0/fps

## Convert frames to a time string
def fr2t(fr, fps):
    return s2t(fr2s(fr, fps))

## Convert frames to a shorter time string
def fr2ts(fr, fps):
    return s2t(fr2s(fr, fps), includems=False)

## Convert seconds to a time string
def s2t(s, includems=True):
    ms = int(1000*(s - int(s)))
    m, s = divmod(int(s), 60)
    h, m = divmod(m, 60)
    return '%i:%02i:%02i.%03i' % (h, m, s, ms) if includems else '%i:%02i:%02i' % (h, m, s)

## Convert seconds to a shorter time string
def s2ts(s):
    return s2t(s, includems=False)

## Shortens a string to a given length, keeping the start and end and placing .. between
def abbv(st, tlen):
    # Minimum length 8
    if tlen < 8:
        raise Exception("MMisc.abbv("+st+","+tlen+"): tlen too short (must be at least 8)")
    if len(st) <= tlen:
        return st
    else:
        tl = int((tlen-2)/2.0)
        return st[:tl]+".."+st[len(st)-tl:]

## Checks whether a value is castable to integer
def isint(st):
    try:
        int(st)
        return True
    except ValueError:
        return False

## Checks whether a value is castable to float
def isnum(st):
    try:
        float(st)
        return True
    except ValueError:
        return False

## Checks whether an extension matches known/common video formats
def isvid(ext):
    if ext in ("avi", "webm", "mkv", "flv", "f4v", "ogv", "avi", "mov", "qt", "wmv", "rm", "asf", "mp4", "m4p", "m4v", "mpg", "mp2", "mpeg", "mpe", "mpv", "m2v", "3gp", "svi", "3g2", "mxf", "roq", "nsv", "yuv", "raw", "mng", "drc"):
        return True
    return False

## Gets the extension of a filename assuming it is a valid filename
def get_ext(filename):
    if filename.find(".") < 0 or filename.find(".") == len(filename)-1:
        return None
    return filename[filename.rfind(".")+1:]