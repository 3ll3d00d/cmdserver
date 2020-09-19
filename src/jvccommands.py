import logging
from enum import Enum

logger = logging.getLogger(__name__)

""" Commands from
 http://pro.jvc.com/pro/attributes/PRESENT/manual/2018_ILA-FPJ_Ext_Command_List_v1.2.pdf
 (replaced by v2.0 https://github.com/nicko88/HTPCRemote/raw/master/IP%20Control%20Spec%20Documents/JVC_NX.pdf)
 http://www.us.jvc.com/projectors/pdf/2018_ILA-FPJ_Remote_Control_Code_Table_V1.1.pdf 
"""


class ReadOnly:
    """Common base class for read-only command arguments"""
    pass


class NoVerify:
    """Common base class for command arguments that cannot be read back"""


class WriteOnly(NoVerify):
    """Common base class for write-only command arguments"""
    pass


class BinaryData:
    """Common base class for binary command arguments"""
    pass


class Model(ReadOnly, Enum):
    """Projector model code"""
    DLA_N7 = b'ILAFPJ -- B2A2'


def s8_bytes_to_list(bstr):
    """Convert 8bit signed bytes to list"""
    return [b if b < 0x80 else b - 0x100 for b in bstr]


def num_to_s8(num):
    """Convert signed number to 8bit (unsigned)"""
    assert -0x80 <= num < 0x80, '{} out of range'.format(num)
    return num & 0xff


def list_to_s8_bytes(numlist):
    """Convert list of signed numbers to 8bit bytes"""
    return bytes(num_to_s8(num) for num in numlist)


def le16_bytes_to_list(bstr):
    """Convert 16bit little-endian bytes to list"""
    i = iter(bstr)
    return [lb + 256*next(i) for lb in i]


def le16_split(table):
    """Split table entries 16bit little-endian byte pairs"""
    for val in table:
        assert not val >> 16
        yield val % 256
        yield int(val / 256)


def list_to_le16_bytes(table):
    """Convert list to 16bit little-endian bytes"""
    return bytes(le16_split(table))


class Numeric(int):
    """Signed 16 bit values as ascii hex data"""
    def __new__(cls, value):
        if isinstance(value, bytes):
            assert len(value) == 4, '{} is not 4 bytes'.format(value)
            cls.value = value
        else:
            assert -0x8000 <= value <= 0x7fff, '{} out of range'.format(value)
            cls.value = bytes('{:04X}'.format(value & 0xffff), 'ascii')
        num = int(cls.value, 16)
        if num & 0x8000:
            num = num - 0x10000
        return super(Numeric, cls).__new__(cls, num)


class NumericReadOnly(ReadOnly, Numeric):
    """Read only numeric value"""
    pass


class CustomGammaTable(BinaryData, list):
    """Custom gamma table data"""
    def __init__(self, value):
        if isinstance(value, bytes):
            assert len(value) == 512, '{} is not 512 bytes'.format(value)
            self.value = value
        else:
            assert len(value) == 256, '{} does not have 256 entries'.format(value)
            self.value = list_to_le16_bytes(value)

        super(CustomGammaTable, self).__init__(le16_bytes_to_list(self.value))


class PanelAlignment(BinaryData, list):
    """Panel Alignment Data"""
    def __init__(self, value):
        if isinstance(value, bytes):
            assert len(value) == 256, '{} is not 256 bytes'.format(value)
            self.value = value
        else:
            assert len(value) == 256, '{} does not have 256 entries'.format(value)
            self.value = list_to_s8_bytes(value)

        super(PanelAlignment, self).__init__(s8_bytes_to_list(self.value))


class SourceAsk(ReadOnly, Enum):
    """Source Asking State"""
    NoSignalOrOutOfRange = b'0'
    SignalAvailable = b'1'


class Null(WriteOnly, Enum):
    """Null command arg"""
    Null = b''


class RemoteCode(WriteOnly, Enum):
    """Remote codes from http://pro.jvc.com/pro/attributes/PRESENT/manual/2018_ILA-FPJ_Remote_Control_Code_Table_V1.1.pdf"""
    Up = b'7301'
    Down = b'7302'
    Back = b'7303'
    On = b'7305'
    Standby = b'7306'
    Input = b'7308'
    Hide = b'731D'
    Anamorphic_A = b'7323'
    Anamorphic_Off = b'7324'
    Aspect_Zoom = b'7327'
    Anamorphic_B = b'732B'
    Menu = b'732E'
    OK = b'732F'
    LensMenu = b'7330'
    Anamorphic_C = b'7333'
    Right = b'7334'
    Left = b'7336'
    CMD_Off = b'7347'
    CMD_Low = b'7348'
    CMD_High = b'7349'
    CMD_IT = b'734A'
    PictureMode_Cinema = b'7368'
    PictureMode_Film = b'7369'
    PictureMode_Natural = b'736A'
    PictureMode_User1 = b'736C'
    PictureMode_User2 = b'736D'
    PictureMode_User3 = b'736E'
    PictureMode_THX = b'736F'
    HDMI1 = b'7370'
    HDMI2 = b'7371'
    Info_PictureAdjust = b'7372'
    Menu_Advanced = b'7373'
    Menu_Info = b'7374'
    Gamma_Toggle = b'7375'
    ColourTemp_Toggle = b'7376'
    ColourProfile_Toggle = b'7388'
    CMD_Toggle = b'738A'
    Aspect_Auto = b'73AE'
    Aspect_Native = b'73AF'
    Anamorphic_Toggle = b'73C5'
    PictureMode_User4 = b'73CA'
    PictureMode_User5 = b'73CB'
    PictureMode_User6 = b'73CC'
    Hide_On = b'73D0'
    Hide_Off = b'73D1'
    Solenoid_Normal = b'73D2'
    Solenoid_Wide = b'73D3'
    Menu_SettingMemory = b'73D4'
    ThreeD_Setting_Toggle = b'73D5'
    ThreeD_Formal_Toggle = b'73D6'
    PictureMode_User_Toggle = b'73D7'
    InstallationMode1 = b'73D8'
    InstallationMode2 = b'73D9'
    InstallationMode3 = b'73DA'
    ThreeD_Format_Auto = b'73DB'
    ThreeD_Format_SideBySide = b'73DC'
    ThreeD_Format_TopAndBottom = b'73DD'
    ThreeD_Format_Off = b'73DE'
    PictureMode_HLG = b'73E1'
    InstallationMode4 = b'73E5'
    InstallationMode5 = b'73E6'
    InstallationMode6 = b'73E7'
    InstallationMode7 = b'73E8'
    InstallationMode8 = b'73E9'
    InstallationMode9 = b'73EA'
    InstallationMode10 = b'73EB'
    PictureMode_HDR10 = b'73ED'
    Menu_MPC = b'73F0'
    Menu_PictureMode = b'73F4'
    Menu_Gamma = b'73F5'
    Menu_NameEdit = b'73F7'
    LowLatency_Toggle = b'73F8'


class PowerState(NoVerify, Enum):
    """Power state"""
    Standby = b'0' # send/get
    LampOn = b'1' # send/get
    Cooling = b'2' # get
    Starting = b'3' # get
    Error = b'4' # get


class PictureMode(Enum):
    """Picture mode"""
    Film = b'00'
    Cinema = b'01'
    Natural = b'03'
    HDR10 = b'04'
    THX = b'06'
    User1 = b'0C'
    User2 = b'0D'
    User3 = b'0E'
    User4 = b'0F'
    User5 = b'10'
    User6 = b'11'
    HLG = b'14'


class InstallationMode(Enum):
    """Installation mode"""
    ONE = b'0'
    TWO = b'1'
    THREE = b'2'
    FOUR = b'3'
    FIVE = b'4'
    SIX = b'5'
    SEVEN = b'6'
    EIGHT = b'7'
    NINE = b'8'
    TEN = b'9'


class IntelligentLensAperture(Enum):
    """Intelligent Lens Aperture Setting"""
    Off = b'0'
    Auto1 = b'1'
    Auto2 = b'2'


class ColorProfile(Enum):
    """Color Profile"""
    Off = b'00'
    Film1 = b'01'
    Film2 = b'02'
    BT709 = b'03'
    Cinema = b'04'
    Anime = b'06'
    Video = b'08'
    HDR = b'0A'
    BT2020 = b'0B'
    THX = b'0D'
    Custom1 = b'0E'
    Custom2 = b'0F'
    Custom3 = b'10'
    Custom4 = b'11'
    Custom5 = b'12'
    DCI = b'21'
    Custom6 = b'22'


class ColorTemperature(Enum):
    """Color Temperature Setting"""
    Temp5500K = b'00'
    Temp6500K = b'02'
    Temp7500K = b'04'
    Temp9300K = b'08'
    HighBright = b'09'
    Custom1 = b'0A'
    Custom2 = b'0B'
    HDR10 = b'0C'
    Xenon1 = b'0D'
    Xenon2 = b'0E'
    HLG = b'14'


class ColorTemperatureCorrection(Enum):
    """Color Temperature Correction Setting"""
    Temp5500K = b'0'
    Temp6500K = b'2'
    Temp7500K = b'4'
    Temp9300K = b'8'
    HighBright = b'9'
    Xenon1 = b'D'
    Xenon2 = b'E'


class GammaTable(Enum):
    """Gamma Table Setting"""
    TwoTwo = b'0'
    Cinema1 = b'1'
    Cinema2 = b'2'
    Custom1 = b'4'
    Custom2 = b'5'
    Custom3 = b'6'
    HDR_HLG = b'7'
    TwoFour = b'8'
    TwoSix = b'9'
    Film1 = b'A'
    Film2 = b'B'
    HDR_PQ = b'C'
    THX = b'10'


class GammaCorrection(Enum):
    """Gamma Correction Setting"""
    Cinema1 = b'01'
    Cinema2 = b'02'
    Import = b'04'
    Gamma1_8 = b'05'
    Gamma1_9 = b'06'
    Gamma2_0 = b'07'
    Gamma2_1 = b'08'
    Gamma2_2 = b'09'
    Gamma2_3 = b'0A'
    Gamma2_4 = b'0B'
    Gamma2_5 = b'0C'
    Gamma2_6 = b'0D'
    Film1 = b'0E'
    Film2 = b'0F'
    HDR_HLQ = b'14'
    HDR_PQ = b'15'


class ColorManagement(Enum):
    Off = b'0'
    On = b'1'


class LowLatency(Enum):
    Off = b'0'
    On = b'1'


class ClearMotionDrive(Enum):
    """Clear Motion Drive Setting"""
    Off = b'0'
    Low = b'3'
    High = b'4'
    InverseTelecine = b'5'


class MotionEnhance(Enum):
    """Motion Enhance Setting"""
    Off = b'0'
    Low = b'1'
    High = b'2'


class LampPower(Enum):
    """Lamp Power Setting"""
    Normal = b'0'
    High = b'1'


class EShift8K(Enum):
    Off = b'0'
    On = b'1'


class GraphicMode(Enum):
    Standard = b'0'
    HighRes = b'1'


class HDMIInputLevel(Enum):
    """HDMI Input Level Setting"""
    Standard = b'0' # 16-235
    Enhanced = b'1' # 0-255
    SuperWhite = b'2' # 16-255
    Auto = b'3'


class HDMIColorSpace(Enum):
    """HDMI Color Space Setting"""
    Auto = b'0'
    YCbCr444 = b'1'
    YCbCr422 = b'2'
    RGB = b'3'


class HDMI2D3D(Enum):
    TwoD = b'0'
    Auto = b'1'
    SideBySide = b'3'
    TopAndBottom = b'4'


class Aspect(Enum):
    Zoom = b'2'
    Auto = b'3'
    Native = b'4'


class MaskData(Enum):
    On = b'1'
    Off = b'2'


class LensControl(Enum):
    Stop = b'0'
    Start = b'1'


class LensImage(Enum):
    Off = b'0'
    On = b'1'


class InstallationStyle(Enum):
    Front = b'0'
    CeilingMountF = b'1'
    Rear = b'2'
    CeilingMountR = b'3'


class Anamorphic(Enum):
    Off = b'0'
    A = b'1'
    B = b'2'
    C = b'3'
    D = b'4'


class PanelAlignmentSwitch(Enum):
    Off = b'0'
    On = b'1'


class HighAltitudeMode(Enum):
    Off = b'0'
    On = b'1'


class BackColour(Enum):
    Blue = b'0'
    Black = b'1'


class MenuPosition(Enum):
    LeftTop = b'0'
    RightTop = b'1'
    Centre = b'2'
    LeftBottom = b'3'
    RightBottom = b'4'
    Left = b'5'
    Right = b'6'


class SourceDisplay(Enum):
    Off = b'0'
    On = b'1'


class Trigger(Enum):
    Off = b'0'
    Power = b'1'
    Anamo = b'2'
    Inst1 = b'3'
    Inst2 = b'4'
    Inst3 = b'5'
    Inst4 = b'6'
    Inst5 = b'7'
    Inst6 = b'8'
    Inst7 = b'9'
    Inst8 = b'A'
    Inst9 = b'B'
    Inst10 = b'C'


class InputState(Enum):
    """Input state"""
    HDMI1 = b'6'
    HDMI2 = b'7'


class SourceData(ReadOnly, str):
    KNOWN_VALUES = {
        b'02': '480p',
        b'03': '576p',
        b'04': '720p50',
        b'05': '720p60',
        b'06': '1080i50',
        b'07': '1080i60',
        b'08': '1080p24',
        b'09': '1080p50',
        b'0A': '1080p60',
        b'0B': 'No Signal',
        b'0C': '720p 3D',
        b'0D': '1080i 3D',
        b'0E': '1080p 3D',
        b'0F': 'Out of Range',
        b'10': '4K(4096)60',
        b'11': '4K(4096)50',
        b'12': '4K(4096)30',
        b'13': '4K(4096)25',
        b'14': '4K(4096)24',
        b'15': '4K(3840)60',
        b'16': '4K(3840)50',
        b'17': '4K(3840)30',
        b'18': '4K(3840)25',
        b'19': '4K(3840)24',
        b'1C': '1080p25',
        b'1D': '1080p30',
        b'1E': '2048x1080 p24',
        b'1F': '2048x1080 p25',
        b'20': '2048x1080 p30',
        b'21': '2048x1080 p50',
        b'22': '2048x1080 p60',
        b'23': '3840x2160 p120',
        b'24': '4096x2160 p120',
        b'25': 'VGA(640x480)',
        b'26': 'VGA(640x480)',
        b'27': 'SVGA(800x600)',
        b'28': 'XGA(1024x768)',
        b'29': 'SXGA(1280x1024)',
        b'2A': 'WXGA(1280x768)',
        b'2B': 'WXGA+(1440x900)',
        b'2C': 'WSXGA+(1680x1050',
        b'2D': 'WUXGA(1920x1200)',
        b'2E': 'WXGA(1280x800)',
        b'2F': 'FWXGA(1366x768)',
        b'30': 'WXGA++(1600x900)',
        b'31': 'UXGA(1600x1200)',
        b'32': 'QXGA'
    }

    """Input Info Source Information"""
    def __new__(cls, value):
        return SourceData.KNOWN_VALUES[value]


class DeepColorData(ReadOnly, str):
    KNOWN_VALUES = {
        b'0': '8 bit',
        b'1': '10 bit',
        b'2': '12 bit',
    }

    """Input Info Deep Color"""
    def __new__(cls, value):
        return DeepColorData.KNOWN_VALUES[value]


class ColorSpaceData(ReadOnly, str):
    KNOWN_VALUES = {
        b'0': 'RGB',
        b'1': 'YUV'
    }

    """Input Info Color Space"""
    def __new__(cls, value):
        return ColorSpaceData.KNOWN_VALUES[value]


class ColorimetryData(ReadOnly, str):
    KNOWN_VALUES = {
        b'0': 'No Data',
        b'1': 'BT.601',
        b'2': 'BT.709',
        b'3': 'xvYCC601',
        b'4': 'xvYCC709',
        b'5': 'sYCC601',
        b'6': 'Adobe YCC601',
        b'7': 'Adobe RGB',
        b'8': 'BT.2020 Constant Luminence',
        b'9': 'BT.2020 Non-Constant Luminence',
        b'A': 'Reserved (Other)'
    }

    def __new__(cls, value):
        return ColorimetryData.KNOWN_VALUES[value]


class HDRData(ReadOnly, str):
    KNOWN_VALUES = {
        b'0': 'SDR',
        b'1': 'HDR',
        b'2': 'SMPTE ST 2084',
        b'F': 'None'
    }

    def __new__(cls, value):
        return HDRData.KNOWN_VALUES[value]


class AutoToneMappingData(ReadOnly, str):
    KNOWN_VALUES = {
        b'0': 'Off',
        b'1': 'On'
    }

    def __new__(cls, value):
        return AutoToneMappingData.KNOWN_VALUES[value]


class Command(Enum):
    """Command codes (and return types)"""
    Null = b'\0\0', Null # NULL command
    Power = b'PW', PowerState # Power [PoWer]
    Input = b'IP', InputState # Input [InPut]
    Remote = b'RC', RemoteCode # Remote control code through [Remote Code]
    GammaRed = b'GR', CustomGammaTable # Gamma data (Red) of the Gamma table ”Custom 1/2/3”
    GammaGreen = b'GG', CustomGammaTable # Gamma data (Green) of the Gamma table ”Custom 1/2/3”
    GammaBlue = b'GB', CustomGammaTable # Gamma data (Blue) of the Gamma table ”Custom 1/2/3”
    PanelAlignRed = b'PR', PanelAlignment # Red of Panel Alignment (zone)
    PanelAlignBlue = b'PB', PanelAlignment # Blue of Panel Alignment (zone)
    SourceAsk = b'SC', SourceAsk # Source asking [SourCe]
    Model = b'MD', Model   # Model status asking [MoDel]
    InstallationMode = b'INML', InstallationMode # Installation Mode switch

    # Picture adjustment [adjustment of Picture] : Picture Adjust
    PictureMode = b'PMPM', PictureMode # Picture Mode switch
    IntelligentLensAperture = b'PMDI', IntelligentLensAperture # Intelligent Lens Aperture
    ColorProfile = b'PMPR', ColorProfile # Color Profile switch (*1)
    ColorTemperatureTable = b'PMCL', ColorTemperature # Color Temperature table
    ColorTemperatureCorrection = b'PMCC', ColorTemperatureCorrection # Color Temperature Correction
    ColorTemperatureGainRed = b'PMGR', Numeric # Color Temperature Gain (Red) adjustment
    ColorTemperatureGainGreen = b'PMGG', Numeric # Color Temperature Gain (Green) adjustment
    ColorTemperatureGainBlue = b'PMGB', Numeric # Color Temperature Gain (Blue) adjustment
    ColorTemperatureOffsetRed = b'PMOR', Numeric # Color Temperature Offset (Red) adjustment
    ColorTemperatureOffsetGreen = b'PMOG', Numeric # Color Temperature Offset (Green) adjustment
    ColorTemperatureOffsetBlue = b'PMOB', Numeric # Color Temperature Offset (Blue) adjustment
    GammaTable = b'PMGT', GammaTable # Gamma Table switch
    PictureToneWhite = b'PMFW', Numeric # Picture Tone (White) adjustment
    PictureToneRed = b'PMFR', Numeric # Picture Tone (Red) adjustment
    PictureToneGreen = b'PMFG', Numeric # Picture Tone (Green) adjustment
    PictureToneBlue = b'PMFB', Numeric # Picture Tone (Blue) adjustment
    Contrast = b'PMCN', Numeric # Contrast adjustment
    Brightness = b'PMBR', Numeric # Brightness adjustment
    Color = b'PMCO', Numeric # Color adjustment
    Tint = b'PMTI', Numeric # Tint adjustment
    NoiseReduction = b'PMRN', Numeric # NR adjustment
    GammaCorrection = b'PMGC', GammaCorrection # Gamma Correction switch
    PMGammaRed = b'PMDR', CustomGammaTable # Gamma Red data
    PMGammaGreen = b'PMDG', CustomGammaTable # Gamma Green data
    PMGammaBlue = b'PMDB', CustomGammaTable # Gamma Blue data
    BrightLevelWhite = b'PMRW', Numeric # Bright Level White
    BrightLevelRed = b'PMRR', Numeric # Bright Level Red
    BrightLevelGreen = b'PMRG', Numeric # Bright Level Green
    BrightLevelBlue = b'PMRB', Numeric # Bright Level Blue
    DarkLevelWhite = b'PMKW', Numeric # Dark Level White
    DarkLevelRed = b'PMKR', Numeric # Dark Level Red
    DarkLevelGreen = b'PMKG', Numeric # Dark Level Green
    DarkLevelBlue = b'PMKB', Numeric # Dark Level Blue
    ColorManagementTable = b'PMCB', ColorManagement # Color Management table
    AxisPositionRed = b'PMAR', Numeric # Axis Position (Red) adjustment
    AxisPositionYellow = b'PMAY', Numeric # Axis Position (Yellow) adjustment
    AxisPositionGreen = b'PMAG', Numeric # Axis Position (Green) adjustment
    AxisPositionCyan = b'PMAC', Numeric # Axis Position (Cyan) adjustment
    AxisPositionBlue = b'PMAB', Numeric # Axis Position (Blue) adjustment
    AxisPositionMagenta = b'PMAM', Numeric # Axis Position (Magenta) adjustment
    HUERed = b'PMHR', Numeric # HUE (Red) adjustment
    HUEYellow = b'PMHY', Numeric # HUE (Yellow) adjustment
    HUEGreen = b'PMHG', Numeric # HUE (Green) adjustment
    HUECyan = b'PMHC', Numeric # HUE (Cyan) adjustment
    HUEBlue = b'PMHB', Numeric # HUE (Blue) adjustment
    HUEMagenta = b'PMHM', Numeric # HUE (Magenta) adjustment
    SaturationRed = b'PMSR', Numeric # Saturation (Red) adjustment
    SaturationYellow = b'PMSY', Numeric # Saturation (Yellow) adjustment
    SaturationGreen = b'PMSG', Numeric # Saturation (Green) adjustment
    SaturationCyan = b'PMSC', Numeric # Saturation (Cyan) adjustment
    SaturationBlue = b'PMSB', Numeric # Saturation (Blue) adjustment
    SaturationMagenta = b'PMSM', Numeric # Saturation (Magenta) adjustment
    BrightnessRed = b'PMLR', Numeric # Brightness (Red) adjustment
    BrightnessYellow = b'PMLY', Numeric # Brightness (Yellow) adjustment
    BrightnessGreen = b'PMLG', Numeric # Brightness (Green) adjustment
    BrightnessCyan = b'PMLC', Numeric # Brightness (Cyan) adjustment
    BrightnessBlue = b'PMLB', Numeric # Brightness (Blue) adjustment
    BrightnessMagenta = b'PMLM', Numeric # Brightness (Magenta) adjustment
    LowLatency = b'PMLL', LowLatency # Low Latency mode
    ClearMotionDrive = b'PMCM', ClearMotionDrive # Clear Motion Drive
    MotionEnhance = b'PMME', MotionEnhance # Motion Enhance
    LensAperture = b'PMLA', Numeric # Lens Aperture
    LampPower = b'PMLP', LampPower # Lamp Power
    EShift8K = b'PMUS', EShift8K # 4K e-shift
    GraphicMode = b'PMGM', GraphicMode
    Enhance = b'PMEN', Numeric # Enhance
    Smoothing = b'PMST', Numeric # Smoothing
    NameEditofPictureModeUser1 = b'PMU1' # Name Edit of Picture Mode User1
    NameEditofPictureModeUser2 = b'PMU2' # Name Edit of Picture Mode User2
    NameEditofPictureModeUser3 = b'PMU3' # Name Edit of Picture Mode User3
    NameEditofPictureModeUser4 = b'PMU4' # Name Edit of Picture Mode User4
    NameEditofPictureModeUser5 = b'PMU5' # Name Edit of Picture Mode User5
    NameEditofPictureModeUser6 = b'PMU6' # Name Edit of Picture Mode User6

    # Picture adjustment [adjustment of Picture] : Input Signal
    HDMIInputLevel = b'ISIL', HDMIInputLevel # HDMI Input Level switch
    HDMIColorSpace = b'ISHS', HDMIColorSpace # HDMI Color Space switch
    HDMI2D3D = b'IS3D' # HDMI 2D/3D switch
    HDMI3DPhase = b'IS3P' # HDMI 3D Phase adjustment
    PicturePositionHorizontal = b'ISPH', Numeric # Picture Position (Horizontal) adjustment
    PicturePositionVertical = b'ISPV', Numeric # Picture Position (Vertical) adjustment
    Aspect = b'ISAS' # Aspect switch
    Mask = b'ISMA' # Mask switch
    MaskLeft = b'ISML', Numeric # Mask (Left) adjustment
    MaskRight = b'ISMR', Numeric # Mask (Right) adjustment
    MaskTop = b'ISMT', Numeric # Mask (Top) adjustment
    MaskBottom = b'ISMB', Numeric # Mask (Bottom) adjustment
    Parallaxof3Dconversion = b'ISLV', Numeric # Parallax of 3D conversion adjustment
    CrosstalkCancelWhite = b'ISCA', Numeric # Crosstalk Cancel (White) adjustment

    # Picture adjustment [adjustment of Picture] : Installation
    FocusNear = b'INFN' # Focus Near adjustment (*3)
    FocusFar = b'INFF' # Focus Far adjustment (*3)
    ZoomTele = b'INZT' # Zoom Tele adjustment (*3)
    ZoomWide = b'INZW' # Zoom Wide adjustment (*3)
    ShiftLeft = b'INSL' # Shift Left adjustment (*3)
    ShiftRight = b'INSR' # Shift Right adjustment (*3)
    ShiftUp = b'INSU' # Shift Up adjustment (*3)
    ShiftDown = b'INSD' # Shift Down adjustment (*3)
    ImagePattern = b'INIP' # Image Pattern switch
    LensLock = b'INLL' # Lens Lock switch
    PixelAdjustHorizontalRed = b'INXR', Numeric # Pixel Adjust (Horizontal Red) adjustment
    PixelAdjustHorizontalBlue = b'INXB', Numeric # Pixel Adjust (Horizontal Blue) adjustment
    PixelAdjustVerticalRed = b'INYR', Numeric # Pixel Adjust (Vertical Red) adjustment
    PixelAdjustVerticalBlue = b'INYB', Numeric # Pixel Adjust (Vertical Blue) adjustment
    InstallationStyle = b'INIS' # Installation Style switch
    KeystoneVertical = b'INKV', Numeric # Keystone (Vertical) adjustment
    Anamorphic = b'INVS', Anamorphic # Anamorphic switch
    ScreenAdjustData = b'INSA', Numeric # Screen Adjust Data
    ScreenAdjust = b'INSC' # Screen Adjust switch
    PanelAlignment = b'INPA' # Panel Alignment switch
    LoadLensmemory = b'INML' # Load Lens memory
    NameEditofLensMemory1 = b'INM1' # Name Edit of Lens Memory 1
    NameEditofLensMemory2 = b'INM2' # Name Edit of Lens Memory 2
    NameEditofLensMemory3 = b'INM3' # Name Edit of Lens Memory 3
    NameEditofLensMemory4 = b'INM4' # Name Edit of Lens Memory 4
    NameEditofLensMemory5 = b'INM5' # Name Edit of Lens Memory 5
    NameEditofLensMemory6 = b'INM6' # Name Edit of Lens Memory 6
    NameEditofLensMemory7 = b'INM7' # Name Edit of Lens Memory 7
    NameEditofLensMemory8 = b'INM8' # Name Edit of Lens Memory 8
    NameEditofLensMemory9 = b'INM9' # Name Edit of Lens Memory 9
    NameEditofLensMemory10 = b'INMA' # Name Edit of Lens Memory 10
    FocusNear1Shot = b'IN1N' # Focus Near adjustment (1 shot)(*3)
    FocusFar1Shot = b'IN1F' # Focus Far adjustment (1 shot) (*3)
    ZoomTele1Shot = b'IN1T' # Zoom Tele adjustment (1 shot) (*3)
    ZoomWide1Shot = b'IN1W' # Zoom Wide adjustment (1 shot) (*3)
    ShiftLeft1Shot = b'IN1L' # Shift Left adjustment (1 shot) (*3)
    ShiftRight1Shot = b'IN1R' # Shift Right adjustment (1 shot) (*3)
    ShiftUp1Shot = b'IN1U' # Shift Up adjustment (1 shot) (*3)
    ShiftDown1Shot = b'IN1D' # Shift Down adjustment (1 shot) (*3)
    HighAltitudeMode = b'INHA' # High Altitude mode switch

    # Picture adjustment [adjustment of Picture] : Display Setup
    BackColor = b'DSBC', BackColour # Back Color switch
    MenuPosition = b'DSMP', MenuPosition # Menu Position switch
    SourceDisplay = b'DSSD', SourceDisplay # Source Display switch
    Logo = b'DSLO' # Logo switch
    Language = b'DSLA' # Language switch

    # Picture adjustment [adjustment of Picture] : Function
    Trigger = b'FUTR' # Trigger switch
    OffTimer = b'FUOT' # Off Timer switch
    EcoMode = b'FUEM' # Eco Mode switch
    Control4 = b'FUCF' # Control4

    # Picture adjustment [adjustment of Picture] : Information
    InfoInput = b'IFIN', InputState # Input display
    InfoSource = b'IFIS', SourceData # Source display
    InfoHorizontalResolution = b'IFRH', NumericReadOnly # Horizontal Resolution display
    InfoVerticalResolution = b'IFRV', NumericReadOnly # Vertical Resolution display
    InfoHorizontalFrequency = b'IFFH', NumericReadOnly # Horizontal Frequency display (*4)
    InfoVerticalFrequency = b'IFFV', NumericReadOnly # Vertical Frequency display (*4)
    InfoDeepColor = b'IFDC', DeepColorData # Deep Color display
    InfoColorSpace = b'IFXV', ColorSpaceData # Color space display
    InfoLampTime = b'IFLT', NumericReadOnly # Lamp Time display
    InfoSoftVersion = b'IFSV' # Soft Version Display
    InfoColorimetry = b'IFCM', ColorimetryData # Colorimetry Display
    InfoHDR = b'IFHR', HDRData
    InfoMaxCLL = b'IFMC', Numeric
    InfoMaxFALL = b'IFMF', Numeric
    PMAutoToneMapping = b'PMTM', AutoToneMappingData
    PMMappingLevel = b'PMTL', Numeric
    LanSetup = b'LS'   # LAN setup [Lan Setup]


def get_all_command_info():
    import sys
    cmds = []
    for command in Command:
        if isinstance(command.value, tuple):
            clazz = getattr(sys.modules[__name__], command.value[1].__name__)
            val = {
                'command_name': command.name,
                'net_code': command.value[0].decode("utf-8"),
                'value_type': command.value[1].__name__,
                'readonly': issubclass(clazz, ReadOnly),
                'writeonly': issubclass(clazz, WriteOnly),
                'binarydata': issubclass(clazz, BinaryData)
            }
            if issubclass(clazz, Enum):
                val['values'] = [i.name for i in clazz]
            elif hasattr(clazz, 'KNOWN_VALUES'):
                val['values'] = {k.decode('utf-8'): v for k, v in getattr(clazz, 'KNOWN_VALUES').items()}
        else:
            val = {
                'code': command.value.decode("utf-8"),
                'writeonly': True
            }
        cmds.append(val)
    return cmds


def load_all_commands():
    cmds = {}
    for command in Command:
        if len(command.value) == 2:
            cmds[command.name] = command.value[1]

    return cmds