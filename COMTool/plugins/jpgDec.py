'''
    @brief This is an example plugin, can receive and send data
    @author
    @date
    @license LGPL-3.0
'''
import os,threading,socket
import re
from PyQt5.QtWidgets import *
from PyQt5.QtCore import pyqtSignal,Qt,QRegExp
from PyQt5.QtGui import *

import struct
import time,threading
import numpy as np
from collections import defaultdict

try:
    from plugins.base import Plugin_Base
    from conn import ConnectionStatus
    from i18n import _
except ImportError:
    from COMTool.plugins.base import Plugin_Base
    from COMTool.i18n import _
    from COMTool.conn import  ConnectionStatus

class Plugin(Plugin_Base):
    hintSignal = None
    id = "jpgDec"
    name = _("JPG解码")
    updateSignal = pyqtSignal(str, bytes)

    def onInit(self, config):
        super().onInit(config)
        self.config = config
        default = {
            'saveJpgPath' : '',
            'saveJpg' : False,
            'jpgLastIndex' : 0,
            'audio_port' : 0,
            'audio_session' : '',
            'audio_token' : 'comtool324d32dfg534gq4gq34gq34',
            'jpg_protocol' : 'tcp' 
        }
        for k in default:
            if not k in self.config:
                self.config[k] = default[k]
        print("jpgDec init")
        self.last_fram_index = 0

    def jpgDebug(self):
        while 1:
            self.fps_label.setText('Fps:' + str(self.fps))
            self.fps = 0
            self.lost_label.setText('lost pack:' + str(self.lost_pack_num))
            time.sleep(1)

    def onConnChanged(self, status:ConnectionStatus, msg:str):
        print("-- connection changed: {}, msg: {}".format(status, msg))

        if status == ConnectionStatus.CONNECTED:
            self.fps_num = 0

    def onWidgetMain(self, parent):
        '''
            main widget, just return a QWidget object
        '''
        self.widget = QWidget()
        layout = QVBoxLayout()
        self.label = QLabel();
        self.label.setMinimumWidth(480)
        layout.setAlignment(Qt.AlignTop)

        layoutDebug = QHBoxLayout()
        self.fps_label = QLabel();
        self.fps_label.setMaximumHeight(20)
        self.fps_label.setMaximumWidth(50)
        self.lost_label = QLabel("lost:");
        layoutDebug.addWidget(self.fps_label)
        layoutDebug.addWidget(self.lost_label)


        layout.addWidget(self.label)
        layout.addLayout(layoutDebug)
        self.widget.setLayout(layout)

        self.updateSignal.connect(self.updateUI)

        return self.widget
    
    def onWidgetSettings(self, parent):
        layout = QVBoxLayout()

        int_validator = QIntValidator()
        int_let_validator = QRegExpValidator(QRegExp('[a-zA-Z0-9]+'))

        settingsLayout = QGridLayout()
        settingsGroupBox = QGroupBox("自动保存")
        self.saveJpgCheckbox = QCheckBox()
        self.saveJpgCheckbox.setToolTip('自动保存接收到的图片')
        self.jpgFilePath = QLineEdit()
        self.jpgFilePath.setReadOnly(True)
        self.jpgFileBtn = QPushButton('路径')

        settingsLayout.addWidget(self.saveJpgCheckbox,1,0,1,1)
        settingsLayout.addWidget(self.jpgFilePath,1,1,1,1)
        settingsLayout.addWidget(self.jpgFileBtn,1,2,1,1)
        settingsGroupBox.setLayout(settingsLayout)
        settingsGroupBox.setAlignment(Qt.AlignHCenter)

        audioPlayerLayout = QGridLayout()
        audioPlayerGroupBox = QGroupBox("播放音频")
        audioPlayerPortText = QLabel("端口")
        self.audioPlayerPort = QLineEdit()
        self.audioPlayerPort.setValidator(int_validator)
        self.audioPlayerPort.setMaxLength(5)
        audioSessionIdText = QLabel("ID")
        self.audioSessionId = QLineEdit()
        self.audioSessionId.setMaxLength(4)
        self.audioSessionId.setValidator(int_let_validator)
        self.audioSessionId.setToolTip('Session ID')
        self.audioPlayerBtn = QPushButton("开启")
        self.audioPlayerBtn.setToolTip('播放声音')

        audioPlayerLayout.addWidget(audioPlayerPortText,1,0,1,1)
        audioPlayerLayout.addWidget(self.audioPlayerPort,1,1,1,1)
        audioPlayerLayout.addWidget(audioSessionIdText,1,2,1,1)
        audioPlayerLayout.addWidget(self.audioSessionId,1,3,1,1)

        audioPlayerLayout.addWidget(self.audioPlayerBtn,2,0,1,5)
        audioPlayerGroupBox.setLayout(audioPlayerLayout)
        audioPlayerGroupBox.setAlignment(Qt.AlignHCenter)


        protocolLayout = QGridLayout()
        layoutProtocol = QHBoxLayout()
        protocolWidget = QWidget()
        protocolGroupBox = QGroupBox("传输协议")
        protocolLabel = QLabel('协议')
        self.protoclJTcpRadioBtn = QRadioButton("TCP")
        self.protoclJUdpRadioBtn = QRadioButton("UDP")
        layoutProtocol.addWidget(self.protoclJTcpRadioBtn)
        layoutProtocol.addWidget(self.protoclJUdpRadioBtn)
        protocolWidget.setLayout(layoutProtocol)
        protocolLayout.addWidget(protocolLabel,0,0)
        protocolLayout.addWidget(protocolWidget,0,1,1,2)
        protocolGroupBox.setLayout(protocolLayout)
        protocolGroupBox.setAlignment(Qt.AlignHCenter)
        
        layout.addWidget(settingsGroupBox)
        layout.addWidget(audioPlayerGroupBox)
        layout.addWidget(protocolGroupBox)

        widget = QWidget()
        widget.setLayout(layout)
        layout.setContentsMargins(0,0,0,0)
        widget.setMinimumWidth(300)


        #event
        self.jpgFileBtn.clicked.connect(self.selectJpgPath)
        self.saveJpgCheckbox.clicked.connect(self.setSaveJpg)
        self.audioPlayerPort.textChanged.connect(lambda: self.setVar('audio_port'))
        self.audioSessionId.textChanged.connect(lambda: self.setVar('audio_session'))
        self.audioPlayerBtn.clicked.connect(self.setAudioPlay)
        self.protoclJTcpRadioBtn.clicked.connect(lambda: self.changeProtocol("tcp"))
        self.protoclJUdpRadioBtn.clicked.connect(lambda: self.changeProtocol("udp"))
        return widget
    
    def changeProtocol(self, protocol):
        if protocol == 'tcp':
            self.config['jpg_protocol'] = 'tcp'
        elif protocol == 'udp':
            self.config['jpg_protocol'] = 'udp'
    
    def onUiInitDone(self):
        if self.config['saveJpgPath'] != '':
            self.jpgFilePath.setText(self.config['saveJpgPath'])
        else :
            self.config['saveJpg'] = False
        self.saveJpgCheckbox.setCheckState(self.config['saveJpg'])
        if self.config['audio_session'] != '':
            self.audioSessionId.setText(self.config['audio_session'])
        if self.config['audio_port'] != 0:
            self.audioPlayerPort.setText(self.config['audio_port'])

        if self.config['jpg_protocol'] == 'tcp':
            self.protoclJTcpRadioBtn.setChecked(True)
        else:
            self.protoclJUdpRadioBtn.setChecked(True)
        self.lost_pack_num = 0
        self.fps = 0
        self.tDebug = threading.Thread(target=self.jpgDebug)
        self.tDebug.setDaemon(True)
        self.tDebug.start()
    
    def onJpgSave(self, frame):
        jpgPath = self.config['saveJpgPath']
        if self.config['saveJpg'] and jpgPath:
            jpgFileName = 'jpeg%04d.jpg'%(self.config['jpgLastIndex']+1)
            with open(os.path.join(jpgPath, jpgFileName), 'wb') as f:
                f.write(frame)
                self.config['jpgLastIndex'] += 1

    def setSaveJpg(self):
        if self.saveJpgCheckbox.isChecked():
            if self.config['saveJpgPath']:
                self.config['saveJpg'] = True
                pattern = r'^jpeg(\d+).jpg$'
                file_names = [name for name in os.listdir(self.config['saveJpgPath']) if re.match(pattern, name)]
                if file_names:
                    file_names.sort(key=lambda name: int(re.match(pattern, name).group(1)))
                    last_file_index = int(re.match(pattern, file_names[-1]).group(1))
                else:
                    last_file_index = 0
                self.config['jpgLastIndex'] = last_file_index
            else:
                self.saveJpgCheckbox.setChecked(False)
                self.hintSignal.emit('error',_('error'), '请先选择文件保存路径')
        else:
            self.config['saveJpg'] = False

    def selectJpgPath(self):
        oldPath = self.jpgFilePath.text()
        if oldPath=='':
            oldPath = os.getcwd()
        fileName_choose = QFileDialog.getExistingDirectory(self.widget, '选择目录', oldPath)
        if fileName_choose == '':
            return
        self.jpgFilePath.setText(fileName_choose)
        self.jpgFilePath.setToolTip(fileName_choose)
        self.config['saveJpgPath'] = fileName_choose

        pattern = r'^jpeg(\d+).jpg$'
        file_names = [name for name in os.listdir(fileName_choose) if re.match(pattern, name)]
        if file_names:
            file_names.sort(key=lambda name: int(re.match(pattern, name).group(1)))
            last_file_index = int(re.match(pattern, file_names[-1]).group(1))
        else:
            last_file_index = 0
        self.config['jpgLastIndex'] = last_file_index

    def setVar(self, key, value=None):
        if key == 'audio_port':
            if self.audioPlayerPort.text() == '':
                self.config[key] = 0
            else:
                self.config[key] = int(self.audioPlayerPort.text())
        if key == 'audio_session':
            self.config[key] = self.audioSessionId.text()
    
    def setAudioPlay(self):
        if self.audioPlayerBtn.text() == '开启':
            if self.config['audio_port'] == 0 or self.config['audio_session']=='':
                self.hintSignal.emit('error',_('error'), '请先设置端口和session id')
            else: 
                self.audioPlayerPort.setReadOnly(True)
                self.audioSessionId.setReadOnly(True)
                self.sockAudio = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.audioPlayerBtn.setText('关闭')
        else:
            self.audioPlayerPort.setReadOnly(False)
            self.audioSessionId.setReadOnly(False)
            self.audioPlayerBtn.setText('开启')

    def updateUI(self, dataType, data : bytes):
        '''
            UI thread
        '''

        if dataType == "jpeg":
            photo  = QPixmap()
            photo.loadFromData(data)
            photo = photo.scaled(self.widget.size(), Qt.KeepAspectRatio)
            self.label.setPixmap(photo)
            self.label.show()
        elif dataType == "fps":
            self.fps_label.setText(data.decode('utf-8'))

    def checkJpgEof(self, data):
        for i in range(len(data) - 1):
            if data[i] == 0xff and data[i+1] == 0xd9:
                return i+2
            
    def prasePack(self, data :bytes, method):
        if len(data):
            header = data[0:4]
            (frame_index, eof_flag, packet_index, pack_total_count) = struct.unpack('BBBB', header)
            if self.last_fram_index != frame_index and packet_index == 1:
                self.last_fram_index = frame_index
                self.pack_length = 0
                self.pack_cnt = 0
                self.frame_data = []

            org_len = len(data)

            if self.last_fram_index == frame_index and self.pack_cnt+1 == packet_index:
                
                if eof_flag == 1 and method == 'tcp':
                    org_len = self.checkJpgEof(data)
                    
                self.frame_data.append((self.pack_cnt, data[4:org_len]))
                self.pack_cnt = packet_index

                if eof_flag == 1:
                    sorted_packets = sorted(self.frame_data, key=lambda x:x[0])
                    data = b''
                    for packet in sorted_packets:
                        data += packet[1]
                    self.frame_data = []
                    self.fps += 1
                    self.updateSignal.emit("jpeg", data)
            elif self.last_fram_index == frame_index and self.pack_cnt+1 != packet_index:
                self.lost_pack_num = packet_index - self.pack_cnt
                self.pack_cnt = packet_index
    
    def onReceived(self, data : bytes):
        '''
            call in receive thread, not UI thread
        '''
        super().onReceived(data)
        self.prasePack(data, self.config['jpg_protocol'])

        
