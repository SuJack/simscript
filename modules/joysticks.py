''' Joystick abstraction layer '''

from ctypes import CDLL, Structure, byref, c_void_p, c_char_p, c_long, c_byte
import logging,traceback,os.path

class Joystick:
    
    def __init__(self, nameOrIndex):
        
        if isinstance(nameOrIndex, int):
            if nameOrIndex < numJoysticks():
                index = nameOrIndex
        else: 
            for j in range(0, numJoysticks()) :
                if nameOrIndex == str(__sdl.SDL_JoystickName(j), "utf-8"):
                    index = j

        try:    
            self.index = index;
        except:
            raise EnvironmentError("joysticks.get('%s') is not available" % nameOrIndex)

        self._handle = c_void_p()
        self.name = str(__sdl.SDL_JoystickName(self.index), "utf-8")
        
    def _acquire(self):
        if self._handle:
            return
        self._handle = __sdl.SDL_JoystickOpen(self.index)
        if not self._handle:
            raise EnvironmentError("joysticks.get('%s') can't be acquired" % self.index)
            
        
    def numAxis(self):
        return __sdl.SDL_JoystickNumAxes(self._handle) if self._handle else 0

    def getAxis(self, i):
        return __sdl.SDL_JoystickGetAxis(self._handle, i) / 32767  if self._handle else 0
    
    def numButtons(self):
        return __sdl.SDL_JoystickNumButtons(self._handle)  if self._handle else 0
    
    def getButton(self, i):
        return __sdl.SDL_JoystickGetButton(self._handle, i)  if self._handle else False
    
    def _sync(self):
        pass
    
    def __str__(self):
        # button/axis information isn't available before acquired
        return "joysticks.get('%s') # index %d" % (self.name, self.index)
    

class VirtualJoystick:
    
    _DEVICE_NAME = 'vJoy Device'

    _AXIS_KEYS = [
        (0x30, "wAxisX"), 
        (0x31, "wAxisY"), 
        (0x32, "wAxisZ"),
        (0x33, "wAxisXRot"),
        (0x34, "wAxisYRot"),
        (0x35, "wAxisZRot"),
        (0x36, "wSlider"),
        (0x37, "wDial"),
        (0x38, "wWheel")
        ]

    class Position(Structure):
        _fields_ = [
          ("index", c_byte),
          ("wThrottle", c_long),
          ("wRudder", c_long),
          ("wAileron", c_long),
          ("wAxisX", c_long),
          ("wAxisY", c_long),
          ("wAxisZ", c_long),
          ("wAxisXRot", c_long), 
          ("wAxisYRot", c_long),
          ("wAxisZRot", c_long),
          ("wSlider", c_long),
          ("wDial", c_long),
          ("wWheel", c_long),
          ("wAxisVX", c_long),
          ("wAxisVY", c_long),
          ("wAxisVZ", c_long),
          ("wAxisVBRX", c_long), 
          ("wAxisVBRY", c_long),
          ("wAxisVBRZ", c_long),
          ("lButtons", c_long),  # 32 buttons: 0x00000001 to 0x80000000 
          ("bHats", c_long),     # Lower 4 bits: HAT switch or 16-bit of continuous HAT switch
          ("bHatsEx1", c_long),  # Lower 4 bits: HAT switch or 16-bit of continuous HAT switch
          ("bHatsEx2", c_long),  # Lower 4 bits: HAT switch or 16-bit of continuous HAT switch
          ("bHatsEx3", c_long)   # Lower 4 bits: HAT switch or 16-bit of continuous HAT switch
          ]
    

    def __init__(self, joysticks, joystick, virtualIndex):
        self.index = joystick.index
        self.name = joystick.name
        
        self._position = VirtualJoystick.Position()
        self._position.index = virtualIndex+1
        
        self._acquired = False

        self._buttons = __vjoy.GetVJDButtonNumber(self._position.index)
        
        self._axis = []
        for akey, pkey in VirtualJoystick._AXIS_KEYS:
            if __vjoy.GetVJDAxisExist(self._position.index, akey):
                amax = c_long()
                amin = c_long()
                __vjoy.GetVJDAxisMin(self._position.index, akey, byref(amin))
                __vjoy.GetVJDAxisMax(self._position.index, akey, byref(amax))
                self._axis.append((pkey, amin.value,amax.value))
                self._position.__setattr__(pkey, int(amin.value + (amax.value-amin.value)/2)) 
                
    def _acquire(self):
        if self._acquired:
            return
        if not __vjoy.AcquireVJD(self._position.index):
            raise EnvironmentError("joysticks.get('%s') is not a free Virtual Joystick" % self.index)
        self._acquired = True
                
    def numAxis(self):
        return len(self._axis)

    def getAxis(self, i):
        if i<0 or i>=len(self._axis):
            raise EnvironmentError("joysticks.get('%s') doesn't have axis %d" % i)
        pkey, amin, amax = self._axis[i] 
        return (self._position.__getattribute__(pkey) - amin) / (amax-amin) * 2 - 1
    
    def setAxis(self, a, value):
        if a<0 or a>=len(self._axis):
            raise EnvironmentError("joysticks.get('%s') doesn't have axis %d" % a)
        if value < -1 or value > 1:
            raise EnvironmentError("joysticks.get('%s') value for axis %d not -1.0 < %d < 1.0" % (self.index, a, value))
        pkey, amin, amax = self._axis[a]
        self._position.__setattr__(pkey, int( (value+1)/2 * (amax-amin) + amin))
    
    def numButtons(self):
        return self._buttons
    
    def getButton(self, i):
        if i<0 or i>=self._buttons:
            raise EnvironmentError("joysticks.get('%s') doesn't have button  %d" % i)
        return self._position.lButtons & (1<<i)
    
    def setButton(self, i, value):
        if i<0 or i>=self._buttons:
            raise EnvironmentError("joysticks.get('%s') doesn't have button  %d" % i)
        if value:
            self._position.lButtons |= 1<<i
        else:
            self._position.lButtons &= ~(1<<i)
        
    def _sync(self):
        if not __vjoy.UpdateVJD(self._position.index, byref(self._position)):
            __log.warning("joysticks.get('%s') couldn't be set" % self.name)
    
    def __str__(self):
        return "joysticks.get('%s') # VirtualJoystick index %d" % (self.name, self.index)
     
def numJoysticks():
    if not __sdl:
        return 0
    return max(__sdl.SDL_NumJoysticks(), len(__joysticks))

def get(nameOrIndex):
    try:
        joy = __name2joystick[nameOrIndex]
    except:
        joy = Joystick(nameOrIndex)
        __name2joystick.__joysticks.append(joy)
        __name2joystick[joy.index] = joy
        __name2joystick[joy.name] = joy 
    joy._acquire()
    return joy


def button(nameOrIndexAndButton):
    """ test button eg button 1 of Saitek Pro Flight Quadrant via button('Saitek Pro Flight Quadrant.1') """
    nameOrIndex, button = nameOrIndexAndButton.split(".")
    return get(nameOrIndex).button(int(button))
    
def sync():
    if __sdl:
        __sdl.SDL_JoystickUpdate()
    for joy in __joysticks:
        joy._sync()
    
def init():    
    global __sdl, __vjoy, __log, __joysticks, __name2joystick
    
    __sdl = None
    __vjoy = None
    __log = logging.getLogger(__name__)
    __joysticks = []
    __name2joystick = dict()

    
    # preload all available joysticks for reporting
    if not __sdl: 
        try:
            __sdl = CDLL(os.path.join("contrib","sdl","SDL.dll"))
            __sdl.SDL_Init(0x200)
            __sdl.SDL_JoystickName.restype = c_char_p
            for index in range(0, __sdl.SDL_NumJoysticks()) :
                joy = Joystick(index)
                __joysticks.append(joy)
        except Exception as e:
            __log.warning("Cannot initialize support for physical Joysticks (%s)" % e)
            __log.debug(traceback.format_exc())
    
    # wrap virtual joysticks where applicable                
    if not __vjoy: 
        try:
            __vjoy = CDLL(os.path.join("contrib", "vjoy", "vJoyInterface.dll"))
            
            if not __vjoy.vJoyEnabled():
                __log.info("No Virtual Joystick Driver active")
                return
    
            numVirtuals = 0
                            
            for i,joy in enumerate(__joysticks):
                if joy.name == VirtualJoystick._DEVICE_NAME:
                    try:
                        virtual = VirtualJoystick(joy, numVirtuals)
                        __joysticks[i] = virtual
                    except Exception as e:
                        __log.warning("Cannot initialize support for virtual Joystick %s (%s)" % (joy.name, e))
                        __log.debug(traceback.format_exc())
                    numVirtuals += 1
                
        except Exception as e:
            __log.warning("Cannot initialize support for virtual Joysticks (%s)" % e)
            __log.debug(traceback.format_exc())
    
    # build dictionary
    for joy in __joysticks:
        __name2joystick[joy.name] = joy 
        __name2joystick._dict[joy.index] = joy 
        __log.info(joy)
    

init()