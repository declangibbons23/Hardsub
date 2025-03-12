import gradio as gr
import os
import shutil
from videocr import save_subtitles_to_file  # Correct import
import requests
import urllib.parse
from tqdm import tqdm

# Define paths - Modified for local Ubuntu environment
HOME_DIR = os.path.expanduser('~')
DATA_DIR = os.path.join(HOME_DIR, 'hardsub_extract_data')
TEMP_DIR = os.path.join(HOME_DIR, '.hardsub_extract_temp')
DEMO_VIDEO_PATH = os.path.join(DATA_DIR, "demo.mp4")
DOWNLOAD_VIDEO_PATH = os.path.join(DATA_DIR, 'video.mp4')

# Ensure directories exist
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

def download_video(url):
    """
    Download video from URL and save as video.mp4 with progress bar
    """
    try:
        # Validate URL
        if not url or not urllib.parse.urlparse(url).scheme:
            raise ValueError("Please provide a valid URL")
        
        # Send a HEAD request first to get the file size
        response = requests.head(url, allow_redirects=True)
        file_size = int(response.headers.get('content-length', 0))
        
        # Download the file with progress bar
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        # Initialize progress bar
        progress = tqdm(
            total=file_size,
            unit='iB',
            unit_scale=True,
            unit_divisor=1024,
            desc=f"Downloading video"
        )
        
        # Save the file as video.mp4 with progress updates
        with open(DOWNLOAD_VIDEO_PATH, 'wb') as f:
            for data in response.iter_content(chunk_size=1024):
                size = f.write(data)
                progress.update(size)
        
        progress.close()
        
        # Get final file size
        final_size = os.path.getsize(DOWNLOAD_VIDEO_PATH)
        download_speed = file_size / progress.format_dict["elapsed"] if progress.format_dict["elapsed"] > 0 else 0
        
        return (f"Video successfully downloaded to {DOWNLOAD_VIDEO_PATH}\n"
                f"Total size: {format_size(final_size)}\n"
                f"Average speed: {format_size(download_speed)}/s")
    
    except Exception as e:
        return f"Error downloading video: {str(e)}"

def format_size(size):
    """Format size in bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0

def list_files():
    try:
        files = os.listdir(DATA_DIR)
        # Filter for .srt files
        srt_files = [f for f in files if f.endswith('.srt')]
        
        # Copy files to temp directory and return temp paths
        temp_paths = []
        for srt_file in srt_files:
            src_path = os.path.join(DATA_DIR, srt_file)
            temp_path = os.path.join(TEMP_DIR, srt_file)
            shutil.copy2(src_path, temp_path)
            temp_paths.append(temp_path)
            
        return temp_paths
    except Exception as e:
        print(f"Error listing files: {str(e)}")
        return []

def run_video_ocr(video_source, video_url, input_video, output_file_name, language_code, start_time, end_time, confidence_threshold, similarity_threshold, brightness_threshold, use_fullframe):
    try:
        # Ensure the output directory exists
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)

        # Determine video path based on source
        if video_source == "Demo Video":
            if not os.path.exists(DEMO_VIDEO_PATH):
                raise ValueError("Demo video not found. Please place a demo.mp4 file in the data directory.")
            video_path = DEMO_VIDEO_PATH
        elif video_source == "URL":
            if not video_url:
                raise ValueError("Please provide a video URL")
            # Download the video first
            download_result = download_video(video_url)
            if "Error" in download_result:
                raise ValueError(download_result)
            video_path = DOWNLOAD_VIDEO_PATH
        else:  # Upload Video
            if not input_video:
                raise ValueError("Please upload a video file")
            video_path = input_video

        # Ensure output filename ends with .srt
        if not output_file_name.endswith('.srt'):
            output_file_name += '.srt'

        # Define full path for the output file
        output_path = os.path.join(DATA_DIR, output_file_name)

        # Save the subtitles to file with correct parameters
        save_subtitles_to_file(
            video_path,
            output_path,
            lang=language_code,
            time_start=start_time,
            time_end=end_time,
            sim_threshold=similarity_threshold,
            conf_threshold=confidence_threshold,
            brightness_threshold=brightness_threshold,
            use_fullframe=use_fullframe
        )

        return f"Subtitle extraction completed! File saved to {output_path}"
    except Exception as e:
        return f"Error: {str(e)}"

def video_ocr_interface():
    with gr.Blocks() as demo:
        gr.Markdown("# Video OCR Interface")
        
        with gr.Row():
            video_source = gr.Radio(
                choices=["Upload Video", "URL", "Demo Video"],
                label="Video Source",
                value="Upload Video"
            )

        with gr.Row():
            # Create both components but manage visibility
            video_url = gr.Textbox(
                label="Video URL",
                placeholder="Enter video URL",
                visible=False  # Initially hidden
            )
            
            input_video = gr.File(
                label="Upload Video",
                type="filepath",
                visible=True  # Initially visible
            )

        with gr.Row():
            output_file_name = gr.Textbox(label="Output File Name (.srt)", value="subtitle.srt")
            language_code = gr.Textbox(label="Language Code", value="ch")
        
        with gr.Row():
            start_time = gr.Textbox(label="Start Time (HH:MM:SS)", value="00:00:00")
            end_time = gr.Textbox(label="End Time (HH:MM:SS)", value="")
        
        with gr.Row():
            confidence_threshold = gr.Slider(label="Confidence Threshold", minimum=0, maximum=100, value=75)
            similarity_threshold = gr.Slider(label="Similarity Threshold", minimum=0, maximum=100, value=80)
            brightness_threshold = gr.Slider(label="Brightness Threshold", minimum=0, maximum=255, value=210)
        
        with gr.Row():
            use_fullframe = gr.Checkbox(label="Use Full Frame", value=True)

        submit_btn = gr.Button("Start OCR")
        output_label = gr.Textbox(label="Status", interactive=False)

        file_list = gr.File(
            label="Downloaded .srt Files",
            file_count="multiple",
            interactive=True,
            type="filepath"
        )

        refresh_btn = gr.Button("Refresh File List")

        def toggle_visibility(choice):
            return (
                gr.update(visible=(choice == "URL")),  # video_url visibility
                gr.update(visible=(choice == "Upload Video"))  # input_video visibility
            )

        # Connect the radio button to the visibility toggle
        video_source.change(
            fn=toggle_visibility,
            inputs=[video_source],
            outputs=[video_url, input_video]
        )

        # Define button click behavior
        submit_btn.click(
            fn=run_video_ocr,
            inputs=[
                video_source, video_url, input_video, output_file_name,
                language_code, start_time, end_time,
                confidence_threshold, similarity_threshold,
                brightness_threshold, use_fullframe
            ],
            outputs=[output_label]
        ).success(fn=list_files, outputs=[file_list])
        
        # Refresh button behavior
        refresh_btn.click(fn=list_files, inputs=[], outputs=[file_list])

    return demo

if __name__ == "__main__":
    # Launch the Gradio interface with local settings
    demo = video_ocr_interface()
    demo.launch(
        server_name="0.0.0.0",  # Allow external access
        server_port=7860,       # Default Gradio port
        share=False,            # Don't create public URL
    )
