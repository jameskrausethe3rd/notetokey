from tkinter import *
from turtle import left
import numpy as np
import pyaudio
import pynput.keyboard as kb
import pynput.mouse as ms
from functools import partial

# Just testing github integration

global num_frames
num_frames = 0

global stream

global input_index
input_index = -1
 
def print_selection(title, var, index):
    global input_index

    if(var.get() == 1):
        l.config(text=title)
        input_index = index
    else:
        l.config(text='Input Device')

def keyPresser(res):
    if res == 'space':
        keyboard.press(kb.Key.space)
    elif res == 'enter':
        keyboard.press(kb.Key.enter)
    elif res == 'back':
        keyboard.press(kb.Key.backspace)
    elif res == 'leftclick':
        mouse.press(ms.Button.left)
    elif res == 'rightclick':
        mouse.press(ms.Button.right)
    else:
        keyboard.press(res)

def keyReleaser(lastKey):
    if lastKey == 'space':
        keyboard.release(kb.Key.space)
    elif lastKey == 'enter':
        keyboard.release(kb.Key.enter)
    elif lastKey == 'back':
        keyboard.release(kb.Key.backspace)
    elif lastKey == 'leftclick':
        mouse.release(ms.Button.left)
    elif lastKey == 'rightclick':
        mouse.release(ms.Button.right)
    else:
        keyboard.release(lastKey)       

def startStream():
    global num_frames
    global stream

    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16,
                                    channels=1,
                                    rate=FSAMP,
                                    input=True,
                                    frames_per_buffer=FRAME_SIZE,
                                    input_device_index=input_index)
    stream.start_stream()

    # Create Hanning window function
    windows = 0.5 * (1 - np.cos(np.linspace(0, 2*np.pi, SAMPLES_PER_FFT, False)))

    # Dictionary of Hz-to-key
    r = {(164): 'space',
        (99):  'escape',
        (105): 'leftclick',
        (117): 'rightclick',
        (128):  'enter',
        (146):  'back',

        (158): 'z',
        (175): 'x',
        (199): 'c',
        (222): 'v',
        (246): 'b',
        (275): 'n',
        (310): 'm',

        (263): 'a',
        (292): 's',
        (328): 'd',
        (369): 'f',
        (416): 'g',
        (468): 'h',
        (521): 'j',
        (585): 'k',
        (656): 'l',

        (351): 'q',
        (392): 'w',
        (439): 'e',
        (492): 'r',
        (556): 't',
        (621): 'y',
        (697): 'u',
        (785): 'i',
        (878): 'o',
        (990): 'p'
        }

    # Print initial text
    print ('sampling at', FSAMP, 'Hz with max resolution of', FREQ_STEP, 'Hz')
    print

    # As long as we are getting data:
    keyDown = "false"
    lastKey = ""
    while stream.is_active():

        window.update()

        # Shift the buffer down and new data in
        buf[:-FRAME_SIZE] = buf[FRAME_SIZE:]
        buf[-FRAME_SIZE:] = np.frombuffer(stream.read(FRAME_SIZE), np.int16)

        # Run the FFT on the windowed buffer
        fft = np.fft.rfft(buf * windows)

        # Get frequency of maximum response in range
        freq = int((np.abs(fft[imin:imax]).argmax() + imin) * FREQ_STEP)

        # Console output once we have a full buffer
        num_frames += 1

        if num_frames >= FRAMES_PER_FFT:
            res = ""
            #print (freq)
            if(freq in r):
                res = r[freq]
            if res == "" and keyDown == "true":
                print (lastKey + " has been released")
                keyReleaser(lastKey)
                keyDown = "false"
                raiseButton(lastKey)
            if res != "" and keyDown == "false":
                print (res + " has been pressed down")
                keyPresser(res)
                keyDown = "true"
                lastKey = res
                lowerButton(res)

def stopStream():
    stream.close()

def lowerButton(letter):
    globals()['button%s' % letter.upper()].config(relief=SUNKEN)

def raiseButton(letter):
    globals()['button%s' % letter.upper()].config(relief=RAISED)

def getInputs():
    p = pyaudio.PyAudio()
    info = p.get_host_api_info_by_index(0)
    numdevices = info.get('deviceCount')

    a = []

    for i in range(0, numdevices):
        if (p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
            inputName = p.get_device_info_by_host_api_device_index(0, i).get('name')
            a.append(inputName)

    return a
######################################################################
# Feel free to play with these numbers. Might want to change NOTE_MIN
# and NOTE_MAX especially for guitar/bass. Probably want to keep
# FRAME_SIZE and FRAMES_PER_FFT to be powers of two.

NOTE_MIN = 20       # C4
NOTE_MAX = 500     # A4
FSAMP = 48000      # Sampling frequency in Hz
FRAME_SIZE = 1024   # How many samples per frame?
FRAMES_PER_FFT = 8  # FFT takes average across how many frames?

######################################################################
# Derived quantities from constants above. Note that as
# SAMPLES_PER_FFT goes up, the frequency step size decreases (so
# resolution increases); however, it will incur more delay to process
# new sounds.

SAMPLES_PER_FFT = FRAME_SIZE*FRAMES_PER_FFT
FREQ_STEP = float(FSAMP)/SAMPLES_PER_FFT

######################################################################
# For printing out notes

#NOTE_NAMES = 'C C# D D# E F F# G G# A A# B'.split()

######################################################################
# These three functions are based upon this very useful webpage:
# https://newt.phys.unsw.edu.au/jw/notes.html

def freq_to_number(f): return 69 + 12*np.log2(f/440.0)
def number_to_freq(n): return 440 * 2.0**((n-69)/12.0)
def note_name(n): return NOTE_NAMES[n % 12] + str(n/12 - 1)

######################################################################
# Ok, ready to go now.
######################################################################

# Get min/max index within FFT of notes we care about.
# See docs for numpy.rfftfreq()
def note_to_fftbin(n): return number_to_freq(n)/FREQ_STEP
imin = max(0, int(np.floor(note_to_fftbin(NOTE_MIN-1))))
imax = min(SAMPLES_PER_FFT, int(np.ceil(note_to_fftbin(NOTE_MAX+1))))

# Allocate space to run an FFT. 
buf = np.zeros(SAMPLES_PER_FFT, dtype=np.float32)

# Instantiate mouse and keyboard objects
keyboard = kb.Controller()
mouse = ms.Controller()

# GUI Settings
window = Tk()
window.title('Note to Key')

# Get inputs into input variable
inputs = getInputs()

# Create a layout for the Devices
inputLayout = LabelFrame(window, text='Devices', padx=20,pady=5)
inputLayout.pack(pady=20,padx=10)

# Create a label for selected device that will be updated with the current selection
l = Label(inputLayout, text='Selected Device')
l.grid(row =0, column=0, padx=5,pady=5,sticky='w')


# For loop for the input Devices and generate the variables and rows for it
for i in range(0, len(inputs)):
    inputName = inputs[i]
    globals()['varName%s' % i] = inputName
    globals()['var%s' % i] = IntVar()
    commandArgs = partial(print_selection, inputName, globals()['var%s' % i], i)
    globals()['c%s' % i] = Checkbutton(inputLayout, text=inputName,variable=globals()['var%s' % i], onvalue=1, offvalue=0, command=commandArgs, anchor='w')
    globals()['c%s' % i].grid(row =i+1, column=0, padx=5,pady=5,sticky='w')


# Create a layout for the Keyboard buttons
keyLayout = LabelFrame(window, text='Keyboard', padx=20,pady=5)
keyLayout.pack(pady=20,padx=10)

# List with lists of each rows
layout= [['Q','W','E','R','T','Y','U','I','O','P'],['A','S','D','F','G','H','J','K','L'],['Z','X','C','V','B','N','M']]

# For loop for the keyboard and generate it into the right layout
# loop goes through the 3 main elements
for j in range(0,len(layout)):
    
    # loop goes through each element in the list
    for i in range(0, len(layout[j])):

        # Creates a variable called buttonX where X is the element inside the list in the list
        # Also creates a Tkinter button with the text of X
        globals()['button%s' % layout[j][i]] = Button(keyLayout, text =layout[j][i])

        # This is for the future where I want to be able to set the frequency for each key
        # globals()['button%s' % layout[j][i]].config(width=4,height=2,relief=RAISED, command=lowerButton)

        # Uses variable buttonX and configures it to the correct width and height
        globals()['button%s' % layout[j][i]].config(width=4,height=2)

        # If/else for the first item to not have the columnspan argument since it can't start at 0
        # Otherwise, the item has a column span of j*2
        if j == 0:
            globals()['button%s' % layout[j][i]].grid(row =j, column=i)
        else:
            globals()['button%s' % layout[j][i]].grid(row =j, column=i, columnspan=j*2)

# Create a layout for the Action buttons
actionLayout = LabelFrame(window, text='Actions', padx=20,pady=5)
actionLayout.pack(pady=20,padx=10)

# List with lists of each rows
misc =[["BACK", "ENTER", "ESC", "SPACE"], ["LEFTCLICK", "RIGHTCLICK"]]

# For loop for the action keys and generate it into the right layout
# loop goes through the 2 main elements
for j in range(0,len(misc)):

    # loop goes through each element in the list
    for i in range(0, len(misc[j])):

        # Creates a variable called buttonX where X is the element inside the list in the list
        # Also creates a Tkinter button with the text of X
        globals()['button%s' % misc[j][i]] = Button(actionLayout, text =misc[j][i])

        # This is for the future where I want to be able to set the frequency for each key
        # globals()['button%s' % layout[j][i]].config(width=4,height=2,relief=RAISED, command=lowerButton)

        # Uses variable buttonX and configures it to the correct width and height
        globals()['button%s' % misc[j][i]].config(width=10,height=2)

        # If/else for the first item to not have the columnspan argument since it can't start at 0
        # Otherwise, the item has a column span of j*3
        if j == 0:
            globals()['button%s' % misc[j][i]].grid(row =j, column=i)
        else:
            globals()['button%s' % misc[j][i]].grid(row =j, column=i,columnspan=j*3)

# Create and pack the Start and Stop button that execute the startStream and stopStream
# functions respectively
button_start = Button(window, text ="Start", command=startStream)
button_start.config(width=20, height=2)
button_stop = Button(window, text ="Stop", command=stopStream)
button_stop.config(width=20, height=2)
button_start.pack()
button_stop.pack(padx=5,pady=5)

# Mainloop
window.mainloop()