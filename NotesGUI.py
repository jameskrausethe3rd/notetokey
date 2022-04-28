from tkinter import *
from turtle import left
import numpy as np
import pyaudio
import pynput.keyboard as kb
import pynput.mouse as ms
from functools import partial

global stream

class letterDictionary:
    assignments = {
            # Each freq should be a full step higher than the last
            # Low E String
            'space':164,
            'esc':99,
            'left click':105, 
            'right click':117, 
            'enter':128,  
            'backspace':146,  

            # A String
            'z':158,
            'x':175, 
            'c':199, 
            'v':222, 
            'b':246, 
            'n':275, 
            'm':310, 

            # D String
            'a':263, 
            's':292, 
            'd':328, 
            'f':369, 
            'g':416, 
            'h':468, 
            'j':521, 
            'k':585, 
            'l':656, 

            # G String
            'q':351, 
            'w':392, 
            'e':439, 
            'r':492, 
            't':556, 
            'y':621, 
            'u':697, 
            'i':785, 
            'o':878, 
            'p':990
            }

class selectedInput:
    input_index = -1

    def setSelectedInput(self, index):
        self.input_index = index

class pyaudioSettings:

    def __init__(self):
        ######################################################################
        # Feel free to play with these numbers. Might want to change NOTE_MIN
        # and NOTE_MAX especially for guitar/bass. Probably want to keep
        # FRAME_SIZE and FRAMES_PER_FFT to be powers of two.

        self.NOTE_MIN = 20       # C4
        self.NOTE_MAX = 500     # A4
        self.FSAMP = 48000      # Sampling frequency in Hz
        self.FRAME_SIZE = 1024   # How many samples per frame?
        self.FRAMES_PER_FFT = 8  # FFT takes average across how many frames?

        ######################################################################
        # Derived quantities from constants above. Note that as
        # SAMPLES_PER_FFT goes up, the frequency step size decreases (so
        # resolution increases); however, it will incur more delay to process
        # new sounds.

        self.SAMPLES_PER_FFT = self.FRAME_SIZE*self.FRAMES_PER_FFT
        self.FREQ_STEP = float(self.FSAMP)/self.SAMPLES_PER_FFT

        self.imin = max(0, int(np.floor(self.note_to_fftbin(self.NOTE_MIN-1))))
        self.imax = min(self.SAMPLES_PER_FFT, int(np.ceil(self.note_to_fftbin(self.NOTE_MAX+1))))

        # Allocate space to run an FFT. 
        self.buf = np.zeros(self.SAMPLES_PER_FFT, dtype=np.float32)
        
    ######################################################################
    # These three functions are based upon this very useful webpage:
    # https://newt.phys.unsw.edu.au/jw/notes.html

    def freq_to_number(self, f): 
        return 69 + 12*np.log2(f/440.0)

    def number_to_freq(self, n): 
        return 440 * 2.0**((n-69)/12.0)

    def note_to_fftbin(self, n): 
        # Get min/max index within FFT of notes we care about.
        # See docs for numpy.rfftfreq()
        return self.number_to_freq(n)/self.FREQ_STEP

def displaySelection(title, var, index):
    if(var.get() == 1):
        currentInput.setSelectedInput(index)
        l.config(text=title)   
    else:
        l.config(text="Please select a device")

def calibrate(key):
    # Calibrate the values of the dictionary holding
    # the frequencies and the cooresponding button
    if key.lower() in letterDictionary.assignments:
        return

def keyPresser(res):
    # Some keys such as space and enter, require a different
    # method to send keystrokes and needs the if statements
    # to catch them
    actions = {'space','enter','backspace','esc'}
    clicks = {'left click': 'left','right click': 'right'}

    # If res matches any values in actions, it passes it
    # to kb.Key[res] so each one doesn't need to be specified
    if res in actions:
        keyboard.press(kb.Key[res])

    # If res matches any values in clicks, it passes it
    # to mb.Button[res] so each one doesn't need to be specified
    elif res in clicks:
        mouse.press(ms.Button[clicks[res]])

    # Else, non-special characters get pressed
    else:
        keyboard.press(res)

def keyReleaser(lastKey):
    # Some keys such as space and enter, require a different
    # method to send keystrokes and needs the if statements
    # to catch them
    actions = {'space','enter','backspace','esc'}
    clicks = {'left click': 'left','right click': 'right'}

    # If res matches any values in actions, it passes it
    # to kb.Key[res] so each one doesn't need to be specified
    if lastKey in actions:
        keyboard.release(kb.Key[lastKey])

    # If res matches any values in clicks, it passes it
    # to mb.Button[res] so each one doesn't need to be specified
    elif lastKey in clicks:
        mouse.release(ms.Button[clicks[lastKey]])

    # Else, non-special characters get released
    else:
        keyboard.release(lastKey)       

def startStream():
    global stream
    settings = pyaudioSettings()

    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16,
                    channels=1,
                    rate=settings.FSAMP,
                    input=True,
                    frames_per_buffer=settings.FRAME_SIZE,
                    input_device_index=currentInput.input_index)

    if currentInput.input_index == -1:
        print("Select input")
        return
    else:
        stream.start_stream()

    # Create Hanning window function
    windows = 0.5 * (1 - np.cos(np.linspace(0, 2*np.pi, settings.SAMPLES_PER_FFT, False)))

    # Dictionary of Hz-to-key
   

    # Print initial text
    print ('sampling at', settings.FSAMP, 'Hz with max resolution of', settings.FREQ_STEP, 'Hz')
    
    # Declare keyDown, lastKey, and num_frames outside of the loop
    # since their value needs to be retained between loops
    keyDown = False
    lastKey = ""
    num_frames = 0

    # As long as we are getting data, register keys. If stream stops, 
    # catch the exception and print it:
    try:
        while stream.is_active():

            # Update the Tkinter window
            window.update()

            # Shift the buffer down and new data in
            settings.buf[:-settings.FRAME_SIZE] = settings.buf[settings.FRAME_SIZE:]
            settings.buf[-settings.FRAME_SIZE:] = np.frombuffer(stream.read(settings.FRAME_SIZE), np.int16)

            # Run the FFT on the windowed buffer
            fft = np.fft.rfft(settings.buf * windows)

            # Get frequency of maximum response in range
            freq = int((np.abs(fft[settings.imin:settings.imax]).argmax() + settings.imin) * settings.FREQ_STEP)

            # Console output once we have a full buffer
            num_frames += 1

            if num_frames >= settings.FRAMES_PER_FFT:

                # res is the value of the current key being held
                res = ""

                #print (freq)

                # If the reported frequency is in the dictionary of values,
                # the designated key is assigned to res
                if(freq in letterDictionary.assignments.values()):
                    key_list = list(letterDictionary.assignments.keys())
                    val_list = list(letterDictionary.assignments.values())
                    position = val_list.index(freq)
                    res = key_list[position]

                # If res is blank,the last held key is released,
                # as well as tells Tkinter to release the key visually
                if res == "" and keyDown == True:
                    print (lastKey + " has been released")
                    keyReleaser(lastKey)
                    keyDown = False
                    raiseButton(lastKey)
                
                # If res has a value,the key is pressed,
                # as well as tells Tkinter to press the key visually
                if res != "" and keyDown == False:
                    print (res + " has been pressed down")
                    keyPresser(res)
                    keyDown = True
                    lastKey = res
                    lowerButton(res)
    
    # catches the exception OSError for when the stop button is pressed
    except OSError:
        print("Stream has stopped")

def stopStream():
    # Closes PyAudio stream
    stream.close()

def lowerButton(letter):
    # Takes value from res, converts to upper, references
    # the correct button for that letter, and sets it to sunken
    globals()['button%s' % letter.upper()].config(relief=SUNKEN)

def raiseButton(letter):
    # Takes value from res, converts to upper, references
    # the correct button for that letter, and sets it to raised
    globals()['button%s' % letter.upper()].config(relief=RAISED)

def getInputs():
    # Creates PyAudio object to variable p, sets info to device inputs
    # and sets numdevices to the deviceCount
    p = pyaudio.PyAudio()
    numdevices = p.get_host_api_info_by_index(0).get('deviceCount')

    # Creates list a with all input names
    a = []

    # For loop to add each input name to a
    for i in range(0, numdevices):
        if (p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
            a.append(p.get_device_info_by_host_api_device_index(0, i).get('name'))

    # returns list a
    return a

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

currentInput = selectedInput()
# For loop for the input Devices and generate the variables and rows for it
for i in range(0, len(inputs)):
    inputName = inputs[i]
    globals()['varName%s' % i] = inputName
    globals()['var%s' % i] = IntVar()
    commandArgs = partial(displaySelection, inputName, globals()['var%s' % i], i)
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

        commandArgs = partial(calibrate, layout[j][i])

        # Creates a variable called buttonX where X is the element inside the list in the list
        # Also creates a Tkinter button with the text of X
        globals()['button%s' % layout[j][i]] = Button(keyLayout, text =layout[j][i])

        # Uses variable buttonX and configures it to the correct width and height
        globals()['button%s' % layout[j][i]].config(width=4,height=2, command=commandArgs)

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
misc =[["BACKSPACE", "ESC"], ["ENTER", "SPACE"], ["LEFT CLICK", "RIGHT CLICK"]]

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
            globals()['button%s' % misc[j][i]].grid(row =j, column=i)

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