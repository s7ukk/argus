export class VoiceAssistant {
  private isListening = false;
  private isSpeaking = false;
  private currentAudio: HTMLAudioElement | null = null;
  private mediaStream: MediaStream | null = null;
  private audioContext: AudioContext | null = null;
  private processor: ScriptProcessorNode | null = null;
  private audioChunks: Float32Array[] = [];

  // Auto-stop on silence for command listening
  private commandSpeakingDetected = false;
  private commandSilenceTimer: any = null;
  private commandTimeoutTimer: any = null;

  // VAD continuous wake word monitoring fields
  private wakeStream: MediaStream | null = null;
  private wakeAudioContext: AudioContext | null = null;
  private wakeProcessor: ScriptProcessorNode | null = null;
  private wakeChunks: Float32Array[] = [];
  private wakePreRoll: Float32Array[] = [];
  private wakeSpeakingDetected = false;
  private wakeSilenceTimer: any = null;
  private isWakeChecking = false;
  private ambientNoiseRms = 0.005;
  private recognition: any = null;
  private wakeWords: string[] = [
    'аргус', 'argus', 'эй аргус', 'hey argus', 'привет аргус', 'hi argus',
    'август', 'аргуст', 'argos', 'агрус', 'аргос', 'артус', 'арбуз', 'аркус',
    'аргуз', 'аргас', 'агус', 'алгус', 'ай аргус', 'слушай аргус', 'аргуса', 'аргусе'
  ];

  constructor(
    private onResult: (text: string) => void,
    private onStatusChange: (listening: boolean) => void,
    private onSpeakingChange: (speaking: boolean) => void
  ) {
    this.setupResumeListeners();
  }

  private setupResumeListeners() {
    const resumeContexts = () => {
      try {
        if (this.wakeAudioContext && this.wakeAudioContext.state === 'suspended') {
          this.wakeAudioContext.resume();
        }
        if (this.audioContext && this.audioContext.state === 'suspended') {
          this.audioContext.resume();
        }
      } catch (e) {}
    };
    window.addEventListener('click', resumeContexts, { passive: true });
    window.addEventListener('keydown', resumeContexts, { passive: true });
    window.addEventListener('focus', resumeContexts, { passive: true });
  }

  public playWakeChime() {
    try {
      const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
      const now = ctx.currentTime;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = 'sine';
      osc.frequency.setValueAtTime(587.33, now); // D5
      osc.frequency.exponentialRampToValueAtTime(880, now + 0.1); // A5

      gain.gain.setValueAtTime(0.15, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.22);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start(now);
      osc.stop(now + 0.22);
    } catch (e) {}
  }

  public async startListening(autoStopOnSilence = true) {
    if (this.isListening) return;
    this.stopSpeaking();

    try {
      this.mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });

      this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      if (this.audioContext.state === 'suspended') {
        await this.audioContext.resume();
      }

      const source = this.audioContext.createMediaStreamSource(this.mediaStream);
      this.processor = this.audioContext.createScriptProcessor(4096, 1, 1);
      this.audioChunks = [];
      this.commandSpeakingDetected = false;

      // Mute microphone loopback to speakers to prevent howling/feedback
      const gain = this.audioContext.createGain();
      gain.gain.value = 0;

      this.processor.onaudioprocess = (e) => {
        if (!this.isListening) return;
        const inputData = e.inputBuffer.getChannelData(0);
        this.audioChunks.push(new Float32Array(inputData));

        if (autoStopOnSilence) {
          // Calculate RMS level
          let sum = 0;
          for (let i = 0; i < inputData.length; i++) {
            sum += inputData[i] * inputData[i];
          }
          const rms = Math.sqrt(sum / inputData.length);

          if (rms > 0.008) {
            this.commandSpeakingDetected = true;
            if (this.commandSilenceTimer) {
              clearTimeout(this.commandSilenceTimer);
              this.commandSilenceTimer = null;
            }
          } else if (this.commandSpeakingDetected) {
            if (!this.commandSilenceTimer) {
              this.commandSilenceTimer = setTimeout(() => {
                this.stopListening();
              }, 850);
            }
          }
        }
      };

      source.connect(this.processor);
      this.processor.connect(gain);
      gain.connect(this.audioContext.destination);

      this.isListening = true;
      this.onStatusChange(true);

      // Timeout after 5s if user never speaks anything
      if (autoStopOnSilence) {
        if (this.commandTimeoutTimer) clearTimeout(this.commandTimeoutTimer);
        this.commandTimeoutTimer = setTimeout(() => {
          if (this.isListening && !this.commandSpeakingDetected) {
            this.stopListening();
          }
        }, 5000);
      }
    } catch (err) {
      console.error('[Argus Voice]: Microphone access error:', err);
      this.isListening = false;
      this.onStatusChange(false);
    }
  }

  public async stopListening() {
    if (!this.isListening) return;
    this.isListening = false;
    this.onStatusChange(false);

    if (this.commandSilenceTimer) {
      clearTimeout(this.commandSilenceTimer);
      this.commandSilenceTimer = null;
    }
    if (this.commandTimeoutTimer) {
      clearTimeout(this.commandTimeoutTimer);
      this.commandTimeoutTimer = null;
    }

    try {
      const inputSampleRate = this.audioContext?.sampleRate || 44100;

      if (this.processor) {
        this.processor.disconnect();
        this.processor = null;
      }
      if (this.mediaStream) {
        this.mediaStream.getTracks().forEach((t) => t.stop());
        this.mediaStream = null;
      }
      if (this.audioContext) {
        try { await this.audioContext.close(); } catch (e) {}
        this.audioContext = null;
      }

      if (this.audioChunks.length === 0) return;

      // Merge recorded chunks
      let totalLength = 0;
      for (const arr of this.audioChunks) totalLength += arr.length;
      const merged = new Float32Array(totalLength);
      let offset = 0;
      for (const arr of this.audioChunks) {
        merged.set(arr, offset);
        offset += arr.length;
      }
      this.audioChunks = [];

      // Only process if user actually spoke (> 0.25s)
      if (totalLength / inputSampleRate < 0.25) return;

      // Downsample float32 samples from hardware rate to 16kHz
      const downsampled = this.downsampleBuffer(merged, inputSampleRate, 16000);
      const wavBase64 = this.encodeWAV(downsampled, 16000);

      // Send to FastAPI STT endpoint
      const res = await fetch('http://127.0.0.1:18274/api/voice/stt', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ audio_base64: wavBase64 })
      });

      if (res.ok) {
        const data = await res.json();
        if (data.success && data.transcript && data.transcript.trim()) {
          this.onResult(data.transcript.trim());
        }
      }
    } catch (err) {
      console.error('[Argus Voice]: STT request error:', err);
    }
  }

  public toggleListening() {
    if (this.isListening) {
      this.stopListening();
    } else {
      this.startListening(true);
    }
  }

  private downsampleBuffer(buffer: Float32Array, inputRate: number, outputRate = 16000): Float32Array {
    if (outputRate >= inputRate) return buffer;
    const ratio = inputRate / outputRate;
    const newLength = Math.round(buffer.length / ratio);
    const result = new Float32Array(newLength);
    let offsetResult = 0;
    let offsetBuffer = 0;
    while (offsetResult < result.length) {
      const nextOffsetBuffer = Math.round((offsetResult + 1) * ratio);
      let accum = 0;
      let count = 0;
      for (let i = offsetBuffer; i < nextOffsetBuffer && i < buffer.length; i++) {
        accum += buffer[i];
        count++;
      }
      result[offsetResult] = count > 0 ? accum / count : 0;
      offsetResult++;
      offsetBuffer = nextOffsetBuffer;
    }
    return result;
  }

  private encodeWAV(samples: Float32Array, sampleRate = 16000): string {
    const buffer = new ArrayBuffer(44 + samples.length * 2);
    const view = new DataView(buffer);

    const writeString = (view: DataView, offset: number, str: string) => {
      for (let i = 0; i < str.length; i++) {
        view.setUint8(offset + i, str.charCodeAt(i));
      }
    };

    writeString(view, 0, 'RIFF');
    view.setUint32(4, 36 + samples.length * 2, true);
    writeString(view, 8, 'WAVE');
    writeString(view, 12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true); // PCM
    view.setUint16(22, 1, true); // Mono
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * 2, true);
    view.setUint16(32, 2, true);
    view.setUint16(34, 16, true);
    writeString(view, 36, 'data');
    view.setUint32(40, samples.length * 2, true);

    let index = 44;
    for (let i = 0; i < samples.length; i++) {
      const s = Math.max(-1, Math.min(1, samples[i]));
      view.setInt16(index, s < 0 ? s * 0x8000 : s * 0x7fff, true);
      index += 2;
    }

    const bytes = new Uint8Array(buffer);
    let binary = '';
    const chunk = 0x8000;
    for (let i = 0; i < bytes.length; i += chunk) {
      binary += String.fromCharCode.apply(null, Array.from(bytes.subarray(i, i + chunk)));
    }
    return btoa(binary);
  }

  public async playBase64Audio(base64Mp3?: string | null, fallbackText?: string) {
    this.stopSpeaking();

    if (base64Mp3 && base64Mp3.length > 50) {
      try {
        const cleanB64 = base64Mp3.replace(/\s+/g, '');
        const audio = new Audio(`data:audio/mpeg;base64,${cleanB64}`);
        audio.volume = 1.0;
        this.currentAudio = audio;
        this.isSpeaking = true;
        this.onSpeakingChange(true);

        audio.onplay = () => {
          this.isSpeaking = true;
          this.onSpeakingChange(true);
        };
        audio.onended = () => {
          this.isSpeaking = false;
          this.onSpeakingChange(false);
          this.currentAudio = null;
        };
        audio.onerror = (e) => {
          console.warn('[Argus Voice]: Audio playback error:', e);
          this.isSpeaking = false;
          this.onSpeakingChange(false);
          this.currentAudio = null;
        };
        await audio.play();
        return;
      } catch (e) {
        console.warn('[Argus Voice]: HTML5 Audio play notice:', e);
      }
    }

    this.isSpeaking = false;
    this.onSpeakingChange(false);
  }

  public stopSpeaking() {
    if (this.currentAudio) {
      try {
        this.currentAudio.pause();
        this.currentAudio.currentTime = 0;
      } catch (e) {}
      this.currentAudio = null;
    }
    this.isSpeaking = false;
    this.onSpeakingChange(false);
    try {
      fetch('http://127.0.0.1:18274/api/voice/stop', { method: 'POST' }).catch(() => {});
    } catch (e) {}
  }

  public startWakeWordMonitoring(customTriggerWords?: string) {
    if (customTriggerWords && customTriggerWords.trim()) {
      this.wakeWords = customTriggerWords
        .split(',')
        .map((w) => w.trim().toLowerCase())
        .filter(Boolean);
    }

    // 1. In standard Chromium/Web, if SpeechRecognition is available and not in Electron, start it
    const isElectron = !!(window as any).electronAPI?.isElectron;
    const SpeechRec = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (SpeechRec && !isElectron) {
      try {
        this.recognition = new SpeechRec();
        this.recognition.continuous = true;
        this.recognition.interimResults = false;
        this.recognition.lang = 'ru-RU';

        this.recognition.onresult = (event: any) => {
          if (this.isListening || this.isSpeaking) return;
          const last = event.results.length - 1;
          const text = event.results[last][0].transcript.trim().toLowerCase();

          for (const trigger of this.wakeWords) {
            if (text.includes(trigger)) {
              this.playWakeChime();
              const command = text.replace(trigger, '').trim();
              if (command.length > 2) {
                this.onResult(command);
              } else {
                this.startListening(true);
              }
              break;
            }
          }
        };

        this.recognition.onerror = () => {
          setTimeout(() => {
            if (this.recognition) {
              try { this.recognition.start(); } catch (e) {}
            }
          }, 1000);
        };

        this.recognition.onend = () => {
          if (this.recognition) {
            try { this.recognition.start(); } catch (e) {}
          }
        };

        this.recognition.start();
        return;
      } catch (e) {
        console.warn('[Argus Voice]: Web SpeechRec unavailable, using VAD audio engine:', e);
      }
    }

    // 2. Hardware-level VAD Wake Word Engine for Electron & Native Windows
    this.startVadWakeEngine();
  }

  private async startVadWakeEngine() {
    if (this.wakeStream) return;

    try {
      this.wakeStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });

      this.wakeAudioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      if (this.wakeAudioContext.state === 'suspended') {
        await this.wakeAudioContext.resume();
      }

      const source = this.wakeAudioContext.createMediaStreamSource(this.wakeStream);
      this.wakeProcessor = this.wakeAudioContext.createScriptProcessor(4096, 1, 1);
      this.wakeChunks = [];
      this.wakePreRoll = [];

      // Gain node with zero gain to mute loopback audio
      const gain = this.wakeAudioContext.createGain();
      gain.gain.value = 0;

      this.wakeProcessor.onaudioprocess = (e) => {
        // Skip audio collection if user is actively in full listening mode or AI is speaking
        if (this.isListening || this.isSpeaking || this.isWakeChecking) {
          this.wakeChunks = [];
          this.wakeSpeakingDetected = false;
          return;
        }

        const input = e.inputBuffer.getChannelData(0);
        
        // Calculate Root Mean Square (RMS) energy
        let sum = 0;
        for (let i = 0; i < input.length; i++) {
          sum += input[i] * input[i];
        }
        const rms = Math.sqrt(sum / input.length);

        // Adapt ambient noise floor
        this.ambientNoiseRms = this.ambientNoiseRms * 0.95 + rms * 0.05;
        const dynamicSpeechThreshold = Math.max(0.0035, this.ambientNoiseRms * 1.4);

        if (rms > dynamicSpeechThreshold) {
          if (!this.wakeSpeakingDetected) {
            this.wakeSpeakingDetected = true;
            // Prepend leading pre-roll frames so first syllable is never lost
            this.wakeChunks = [...this.wakePreRoll];
          }
          this.wakeChunks.push(new Float32Array(input));
          if (this.wakeSilenceTimer) {
            clearTimeout(this.wakeSilenceTimer);
            this.wakeSilenceTimer = null;
          }
        } else if (this.wakeSpeakingDetected) {
          // Trailing speech frames
          this.wakeChunks.push(new Float32Array(input));
          if (!this.wakeSilenceTimer) {
            this.wakeSilenceTimer = setTimeout(() => {
              this.processVadWakePhrase();
            }, 750);
          }
        } else {
          // Keep a rolling buffer of 5 frames (~400ms) as pre-roll
          this.wakePreRoll.push(new Float32Array(input));
          if (this.wakePreRoll.length > 5) {
            this.wakePreRoll.shift();
          }
        }
      };

      source.connect(this.wakeProcessor);
      this.wakeProcessor.connect(gain);
      gain.connect(this.wakeAudioContext.destination);
    } catch (err) {
      console.warn('[Argus Voice]: Background VAD wake monitoring error:', err);
    }
  }

  private async processVadWakePhrase() {
    this.wakeSilenceTimer = null;
    this.wakeSpeakingDetected = false;

    if (this.isListening || this.isSpeaking || this.isWakeChecking || this.wakeChunks.length === 0) {
      this.wakeChunks = [];
      return;
    }

    const inputRate = this.wakeAudioContext?.sampleRate || 44100;
    let totalLength = 0;
    for (const arr of this.wakeChunks) totalLength += arr.length;

    // Minimum 0.25 seconds and maximum 12.0 seconds of audio
    const durationSec = totalLength / inputRate;
    if (durationSec < 0.25 || durationSec > 12.0) {
      this.wakeChunks = [];
      return;
    }

    const merged = new Float32Array(totalLength);
    let offset = 0;
    for (const arr of this.wakeChunks) {
      merged.set(arr, offset);
      offset += arr.length;
    }
    this.wakeChunks = [];

    this.isWakeChecking = true;
    try {
      const downsampled = this.downsampleBuffer(merged, inputRate, 16000);
      const wavB64 = this.encodeWAV(downsampled, 16000);

      const res = await fetch('http://127.0.0.1:18274/api/voice/wake-check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          audio_base64: wavB64,
          wake_words: this.wakeWords.join(',')
        })
      });

      if (res.ok) {
        const data = await res.json();
        if (data.wake_detected) {
          this.playWakeChime();
          if (data.command && data.command.trim().length >= 2) {
            this.onResult(data.command.trim());
          } else {
            // Wake word alone detected ("Аргус" / "Привет Аргус") -> activate listening mode with auto-stop
            this.startListening(true);
          }
        }
      }
    } catch (e) {
      console.warn('[Argus Voice]: Wake check error:', e);
    } finally {
      this.isWakeChecking = false;
    }
  }

  public stopWakeWordMonitoring() {
    if (this.recognition) {
      const rec = this.recognition;
      this.recognition = null;
      try { rec.stop(); } catch (e) {}
    }

    if (this.wakeSilenceTimer) {
      clearTimeout(this.wakeSilenceTimer);
      this.wakeSilenceTimer = null;
    }

    if (this.wakeProcessor) {
      this.wakeProcessor.disconnect();
      this.wakeProcessor = null;
    }

    if (this.wakeStream) {
      this.wakeStream.getTracks().forEach((t) => t.stop());
      this.wakeStream = null;
    }

    if (this.wakeAudioContext) {
      try { this.wakeAudioContext.close(); } catch (e) {}
      this.wakeAudioContext = null;
    }
  }
}
