// Self-authored offline fixture generator using Windows' installed System.Speech.
using System;
using System.IO;
using System.Text;
using System.Speech.Synthesis;
using System.Speech.AudioFormat;
using System.Web.Script.Serialization;

public class SpeechWord { public string text { get; set; } public string output { get; set; } }
public class SpeechRequest { public string voice { get; set; } public SpeechWord[] words { get; set; } }
public class SyntheticSpeech {
    public static int Main(string[] args) {
        try {
            var request = new JavaScriptSerializer().Deserialize<SpeechRequest>(File.ReadAllText(args[0], Encoding.UTF8));
            using (var engine = new SpeechSynthesizer()) {
                engine.SelectVoice(request.voice);
                engine.Rate = 0;
                var format = new SpeechAudioFormatInfo(48000, AudioBitsPerSample.Sixteen, AudioChannel.Mono);
                foreach (var word in request.words) {
                    if (File.Exists(word.output)) throw new IOException("Use a new synthetic speech output path");
                    engine.SetOutputToWaveFile(word.output, format);
                    engine.Speak(word.text);
                    engine.SetOutputToNull();
                }
            }
            return 0;
        } catch (Exception e) { Console.Error.WriteLine(e.ToString()); return 1; }
    }
}
