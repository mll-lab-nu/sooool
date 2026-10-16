"""Compose a seeded electronic instrumental and mux it without changing video packets.

No external recordings, music model calls, vocals or copyrighted song transcription.
Requires numpy, scipy and ffmpeg. Input and output must be different files.
"""
import argparse,hashlib,json,pathlib,subprocess,tempfile
import numpy as np
from scipy import signal
from scipy.io import wavfile

def probe(p):
    return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=codec_type,codec_name,width,height,nb_frames,r_frame_rate','-show_entries','format=duration','-of','json',str(p)]))
def video_hash(p):
    return subprocess.check_output(['ffmpeg','-v','error','-i',str(p),'-map','0:v:0','-c','copy','-f','hash','-hash','sha256','-'],text=True).strip()
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=pathlib.Path);p.add_argument('output',type=pathlib.Path);a=p.parse_args()
    if a.source.resolve()==a.output.resolve():p.error('Keep the source video intact')
    if a.output.exists():p.error('Output must be new')
    a.output.parent.mkdir(parents=True,exist_ok=True)
    duration=float(probe(a.source)['format']['duration']);sr=48000;n=int(round(duration*sr));mix=np.zeros((n,2),np.float32);rng=np.random.default_rng(304);beat=60/112
    def put(y,start,gain=1,pan=0):
        i=int(start*sr)
        if i>=n:return
        y=np.asarray(y,dtype=np.float32)[:n-i]*gain
        mix[i:i+len(y),0]+=y*np.sqrt((1-pan)/2);mix[i:i+len(y),1]+=y*np.sqrt((1+pan)/2)
    def note(midi,length,kind):
        t=np.arange(int(length*sr))/sr;f=440*2**((midi-69)/12)
        if kind=='pad':
            y=(np.sin(2*np.pi*f*t)+.3*np.sin(2*np.pi*f*1.003*t)+.15*np.sin(4*np.pi*f*t));env=np.minimum(t/.35,1)*np.minimum((length-t)/.55,1)
        elif kind=='bass':
            y=np.sin(2*np.pi*f*t)+.22*np.sin(4*np.pi*f*t);env=np.minimum(t/.008,1)*np.exp(-t*4)*np.minimum((length-t)/.04,1)
        else:
            y=np.sin(2*np.pi*f*t)+.23*np.sin(4*np.pi*f*t)+.08*np.sin(6*np.pi*f*t);env=np.minimum(t/.004,1)*np.exp(-t*9)
        return y*env
    chords=[(40,55,59,62),(36,55,60,64),(43,55,59,62),(38,54,57,62)]
    # Eight-bar introduction, gently moving harmony, quiet four-on-the-floor groove.
    for bar in range(int(np.ceil(duration/(4*beat)))):
        start=bar*4*beat;root,*tones=chords[(bar//2)%4]
        for j,m in enumerate(tones):put(note(m,4*beat+.2,'pad'),start,.045,[-.55,0,.55][j])
        for step in range(8):
            when=start+step*beat/2
            if bar>=2:put(note(root+(12 if step==6 else 0),beat*.43,'bass'),when,.16)
            if bar>=4:
                m=tones[[0,1,2,1,0,2,1,2][step]]+12
                put(note(m,beat*.7,'pluck'),when,.048 if step%2 else .065,(-.4 if step%2 else .4))
        if bar>=2:
            for b in range(4):
                t=np.arange(int(.23*sr))/sr;phase=2*np.pi*(48*t+90*.025*(1-np.exp(-t/.025)));kick=np.sin(phase)*np.exp(-t*24)+rng.normal(0,.025,len(t))*np.exp(-t*170);put(kick,start+b*beat,.24)
            for b in [1,3]:
                t=np.arange(int(.17*sr))/sr;noise=rng.normal(0,1,len(t));noise=signal.sosfilt(signal.butter(2,1500,'highpass',fs=sr,output='sos'),noise);snare=(.4*noise+.2*np.sin(2*np.pi*180*t))*np.exp(-t*28);put(snare,start+b*beat,.095)
            for step in range(8):
                t=np.arange(int(.055*sr))/sr;noise=rng.normal(0,1,len(t));hat=signal.sosfilt(signal.butter(2,7000,'highpass',fs=sr,output='sos'),noise)*np.exp(-t*100);put(hat,start+(step+.5)*beat/2,.033,(-.3 if step%2 else .3))
    # A quiet stereo echo and soft dynamics; normalize the final AAC to -22 LUFS.
    delay=int(.75*beat*sr);mix[delay:]+=mix[:-delay,::-1].copy()*.13
    t=np.arange(n)/sr;fade=np.minimum(t/1.8,1)*np.minimum((duration-t)/3.5,1);mix*=fade[:,None]
    mix=np.tanh(mix*.9);mix*=.7/max(.001,float(np.max(np.abs(mix))))
    with tempfile.TemporaryDirectory(prefix='racing-score-') as td:
        wav=pathlib.Path(td)/'instrumental.wav';wavfile.write(wav,sr,(mix*32767).astype(np.int16))
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(a.source),'-i',str(wav),'-map','0:v:0','-map','1:a:0','-c:v','copy','-af','loudnorm=I=-22:TP=-2:LRA=6','-c:a','aac','-b:a','192k','-ar','48000','-t',str(duration),'-movflags','+faststart',str(a.output)],check=True)
    before=video_hash(a.source);after=video_hash(a.output);assert before==after
    result=probe(a.output);assert abs(float(result['format']['duration'])-duration)<.06;assert any(s['codec_type']=='audio' for s in result['streams'])
    audit={'music':'original procedurally composed electronic instrumental','seed':304,'tempo_bpm':112,'source_video_sha256':hashlib.sha256(a.source.read_bytes()).hexdigest(),'unchanged_encoded_video_sha256':after,'video_packets_identical':True,'music_target_lufs':-22,'fade_in_s':1.8,'fade_out_s':3.5,'no_external_recordings_or_model_calls':True,'probe':result}
    a.output.with_suffix('.music-audit.json').write_text(json.dumps(audit,indent=2));print(json.dumps(audit))
if __name__=='__main__':main()
