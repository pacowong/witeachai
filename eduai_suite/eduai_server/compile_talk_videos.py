import pandas
import random
import os
import glob

import hashlib
import pandas
from gtts import gTTS 
import hashlib


########## USER CONFIGURATION ##########
EDUAI_PROJ_NAME = 'big_cat_fact_proj'
# Path to Witeach.ai home
EDUAI_SUITE_HOME = r'E:/OpenEcosystem/aris/eduai_suite/'

# Path to a sample talking head video
WAV2LIP_FACE_VIDEO = r'E:/OpenEcosystem/aris/eduai_suite/Wav2Lip/videos/liz_bellward_zoologist.mp4' 
WAV2LIP_PROG = os.path.join(EDUAI_SUITE_HOME, 'Wav2Lip', 'multi_inference.py')
WAV2LIP_CKPT = os.path.join(EDUAI_SUITE_HOME, 'Wav2Lip', 'checkpoints', 'wav2lip_gan.pth')

######################################################
EDUAI_SERVER_HOME = os.path.join(EDUAI_SUITE_HOME, 'eduai_server')
FLASK_HOME = os.path.join(EDUAI_SERVER_HOME, 'flask_chatbot')
FLASK_STATIC_FOLDER = os.path.join(FLASK_HOME, 'static')

EDUAI_PROJ_RESP_VOICES_FOLDER = os.path.join(FLASK_STATIC_FOLDER, 'projs', EDUAI_PROJ_NAME, 'responses_voices')
EDUAI_PROJ_RESP_VIDEOS_FOLDER = os.path.join(FLASK_STATIC_FOLDER, 'projs', EDUAI_PROJ_NAME, 'responses_videos')
EDUAI_PROJ_RESP_KNOWLEDGEBASE_FOLDER = os.path.join(EDUAI_SERVER_HOME, "instance", EDUAI_PROJ_NAME, "responses")

os.makedirs(EDUAI_PROJ_RESP_VOICES_FOLDER, exist_ok=True)
os.makedirs(os.path.join(FLASK_STATIC_FOLDER, 'projs', EDUAI_PROJ_NAME, 'responses_videos'), exist_ok=True)

def audio_to_talk_video(audio, output_dir):
    os.system(f"python {WAV2LIP_PROG} --checkpoint_path {WAV2LIP_CKPT} --face {WAV2LIP_FACE_VIDEO} --audio {audio} --outdir {output_dir}")


def text_to_audio(msg, output_file):
    speech = gTTS(text=msg, lang='en', slow=False)
    speech.save(output_file)


def response_to_audio_and_talk_video(msgs):
    mp3_folder_path = EDUAI_PROJ_RESP_VOICES_FOLDER
    print("Generating response voices")
    for msg in msgs:
        m = hashlib.sha224()
        m.update(msg.strip().encode("utf-8"))
        msg_fname = m.hexdigest()
        mp3_fpath = os.path.join(mp3_folder_path, msg_fname + '.mp3')
        if os.path.isfile(mp3_fpath):
            continue
        text_to_audio(msg, mp3_fpath)
    
    print("Generating response videos")
    mp4_folder_path = EDUAI_PROJ_RESP_VIDEOS_FOLDER
    audio_to_talk_video(os.path.join(mp3_folder_path, "*.mp3"), mp4_folder_path)


def compile_audio_visual_response():
    input_response_data_folder = EDUAI_PROJ_RESP_KNOWLEDGEBASE_FOLDER
    input_response_data_path = glob.glob(os.path.join(input_response_data_folder, "*.txt"))
    print(f"Collecting intent responses from {input_response_data_folder}")
    resp_msgs = []
    for responses_fpath in input_response_data_path:
        print(f"Loading responses from {responses_fpath}")
        resp_df = pandas.read_csv(responses_fpath, sep='\t', encoding='utf-8', quotechar='"')
        for resp_df_idx in range(0, resp_df['wit_response'].count()):
            resp_msg = resp_df['wit_response'].iloc[resp_df_idx]
            resp_msgs.append(resp_msg)

    resp_msgs.append("Sorry, I don't understand your question. I can only answer questions within the topic.")
    resp_msgs.append("Sorry, I don't understand your question. Please ask your teacher for help.")
    response_to_audio_and_talk_video(resp_msgs)
        
if __name__ == "__main__":
    compile_audio_visual_response()

