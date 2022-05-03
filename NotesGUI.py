from concurrent.futures import thread
from tkinter import *
from tkinter import messagebox
from tkinter import filedialog
from threading import *
import time
import json
import pickle
import numpy as np
import pyaudio
import pynput.keyboard as kb
import pynput.mouse as ms
from functools import partial

global stream

class letterDictionary:
    # assignments = {# Each freq should be a full step higher than the last
    #         # Low E String
    #         'space':164,
    #         'esc':99,
    #         'left click':105, 
    #         'right click':117, 
    #         'enter':128,  
    #         'backspace':146,  

    #         # A String
    #         'z':158,
    #         'x':175, 
    #         'c':199, 
    #         'v':222, 
    #         'b':246, 
    #         'n':275, 
    #         'm':310, 

    #         # D String
    #         'a':263, 
    #         's':292, 
    #         'd':328, 
    #         'f':369, 
    #         'g':416, 
    #         'h':468, 
    #         'j':521, 
    #         'k':585, 
    #         'l':656, 

    #         # G String
    #         'q':351, 
    #         'w':392, 
    #         'e':439, 
    #         'r':492, 
    #         't':556, 
    #         'y':621, 
    #         'u':697, 
    #         'i':785, 
    #         'o':878, 
    #         'p':990
    #         }
    assignments = {}

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
        self.FRAME_SIZE = 512   # How many samples per frame?
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

class keyBoardLayout:
    order = [
        ['Q','W','E','R','T','Y','U','I','O','P'],
        ['A','S','D','F','G','H','J','K','L'],
        ['Z','X','C','V','B','N','M']]

def displaySelection(title, var, index):
    if(var.get() == 1):
        currentInput.setSelectedInput(index)
        l.config(text=title)   
    else:
        l.config(text="Please select a device")

def clearAssignments():
    letters.assignments = {}
    messagebox.showinfo("Clear", "Assignments Cleared!")

def saveAssignments():
    try:
        folder_path = filedialog.asksaveasfile(defaultextension='.csv', filetypes=[("csv files", '*.csv')],title="Choose filename").name     
        with open(folder_path, 'w') as convert_file:
            convert_file.write(json.dumps(letters.assignments))
        messagebox.showinfo("Save", "Assignments Saved!")

        currentFile = folder_path.split('/')[-1]
        window.title('Note to Key - ' + currentFile)
    except AttributeError:
        messagebox.showinfo("Save", "No file specified")
    except:
        messagebox.showinfo("Save", "Error")

def loadAssignments():
    try:
        folder_path = filedialog.askopenfilename(defaultextension='.csv', filetypes=[("csv files", '*.csv')],title="Choose filename")   
        with open(folder_path, "r") as scan:
            str = eval(scan.read())
            letters.assignments = str
        messagebox.showinfo("Save", "Assignments loaded!")

        currentFile = folder_path.split('/')[-1]
        window.title('Note to Key - ' + currentFile)
    except:
        messagebox.showinfo("Load", "No file specified")

def showAssignments():
    deez = ''
    for key in letters.assignments:
        deez += ("Key: " + str(key) + ' Freq: ' + str(letters.assignments[key]) + '\n')
    messagebox.showinfo("Show", deez)

def calibrate(key, letters):
    # Calibrate the values of the dictionary holding
    # the frequencies and the cooresponding button
    print("play note for 2 seconds")
    time.sleep(2)
    freq = getFreq()
    letters.assignments[key.lower()] = freq
    messagebox.showinfo("Calibrate", "Done!")

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
        button_start.config(background='green')


    # Create Hanning window function
    windows = 0.5 * (1 - np.cos(np.linspace(0, 2*np.pi, settings.SAMPLES_PER_FFT, False)))

    # Dictionary of Hz-to-key
   

    # Print initial text
    print ('sampling at', settings.FSAMP, 'Hz with max resolution of', settings.FREQ_STEP, 'Hz')
    
    print(letters.assignments)

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

                print (freq)

                # If the reported frequency is in the dictionary of values,
                # the designated key is assigned to res
                if(freq in letters.assignments.values()):
                    key_list = list(letters.assignments.keys())
                    val_list = list(letters.assignments.values())
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

def getFreq():
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
    
    # Declare keyDown, lastKey, and num_frames outside of the loop
    # since their value needs to be retained between loops
    keyDown = False
    lastKey = ""
    num_frames = 0

    # As long as we are getting data, register keys. If stream stops, 
    # catch the exception and print it:
    try:
        for i in range(200):

            # Update the Tkinter window
            window.update()

            # Shift the buffer down and new data in
            settings.buf[:-settings.FRAME_SIZE] = settings.buf[settings.FRAME_SIZE:]
            settings.buf[-settings.FRAME_SIZE:] = np.frombuffer(stream.read(settings.FRAME_SIZE), np.int16)

            # Run the FFT on the windowed buffer
            fft = np.fft.rfft(settings.buf * windows)

            # Get frequency of maximum response in range
            freq = int((np.abs(fft[settings.imin:settings.imax]).argmax() + settings.imin) * settings.FREQ_STEP)
        stream.close()
    except OSError:
        print("Calibration Complete")

    return freq

def stopStream():
    # Closes PyAudio stream
    stream.close()
    button_start.config(background='SystemButtonFace')

def lowerButton(letter):
    # Takes value from res, converts to upper, references
    # the correct button for that letter, and sets it to sunken
    globals()['button%s' % letter.upper()].config(relief=SUNKEN, background='green')

def raiseButton(letter):
    # Takes value from res, converts to upper, references
    # the correct button for that letter, and sets it to raised
    globals()['button%s' % letter.upper()].config(relief=RAISED,background='SystemButtonFace')

def threading():
    # Implement threading
    # t1=Thread(target=startStream)
    # t1.start()
    return

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
inputLayout = LabelFrame(window, text='Devices')
inputLayout.grid(row=0,column=0,sticky='nw', padx=20,pady=(20,0))

# Create a label for selected device that will be updated with the current selection
l = Label(inputLayout, text='Selected Device')
l.grid(row =0, column=0, padx=5,pady=5,sticky='w')

# Instantiates selectedInput object to currentInput
currentInput = selectedInput()

# Instantiates letterDictionary object to letters
letters = letterDictionary()

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
keyLayout.grid(row=1,column=0, sticky='w', padx=20)

# List with lists of each rows
layout = keyBoardLayout()

# For loop for the keyboard and generate it into the right layout
# loop goes through the 3 main elements
for j in range(0,len(layout.order)):
    
    # loop goes through each element in the list
    for i in range(0, len(layout.order[j])):

        commandArgs = partial(calibrate, layout.order[j][i], letters)

        # Creates a variable called buttonX where X is the element inside the list in the list
        # Also creates a Tkinter button with the text of X
        globals()['button%s' % layout.order[j][i]] = Button(keyLayout, text =layout.order[j][i])

        # Uses variable buttonX and configures it to the correct width and height
        globals()['button%s' % layout.order[j][i]].config(width=4,height=2, command=commandArgs)

        # If/else for the first item to not have the columnspan argument since it can't start at 0
        # Otherwise, the item has a column span of j*2
        if j == 0:
            globals()['button%s' % layout.order[j][i]].grid(row =j, column=i)
        else:
            globals()['button%s' % layout.order[j][i]].grid(row =j, column=i, columnspan=j*2)

# Create a layout for the Action buttons
actionLayout = LabelFrame(window, text='Actions', padx=20,pady=5)
actionLayout.grid(row=1,column=0, sticky='e',padx=20)

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

buttonsLayout = LabelFrame(window, text='Functions',padx=20,pady=5)
buttonsLayout.grid(row=2,column=0, padx=20,pady=(0,20),sticky='nw')

# Create and pack the Start and Stop button that execute the startStream and stopStream
# functions respectively
button_start = Button(buttonsLayout, text ="Start", command=startStream)
button_start.config(width=20, height=2)
button_stop = Button(buttonsLayout, text ="Stop", command=stopStream)
button_stop.config(width=20, height=2)
button_clear = Button(buttonsLayout, text ="Clear", command=clearAssignments)
button_clear.config(width=20, height=2)
button_save = Button(buttonsLayout, text ="Save", command=saveAssignments)
button_save.config(width=20, height=2)
button_load = Button(buttonsLayout, text ="Load", command=loadAssignments)
button_load.config(width=20, height=2)
button_show = Button(buttonsLayout, text ="Show", command=showAssignments)
button_show.config(width=20, height=2)

button_start.grid(row=1,column=0)
button_stop.grid(row=1,column=1)
button_save.grid(row=0,column=0)
button_load.grid(row=0,column=1)
button_clear.grid(row=0,column=2)
button_show.grid(row=0,column=3)


# Mainloop
window.mainloop()