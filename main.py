from typing import Optional

import streamlit as st
from streamlit_drawable_canvas import st_canvas
from PIL import Image

from sd2.generate import PIPELINE_NAMES, generate

DEFAULT_PROMPT = "a painting of Childrens books style"
DEFAULT_NEGATIVE_PROMPT = "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry, artist name"
DEFAULT_WIDTH, DEFAULT_HEIGHT = 512, 512
OUTPUT_IMAGE_KEY = "output_img"
LOADED_IMAGE_KEY = "loaded_image"


def get_image(key: str) -> Optional[Image.Image]:
    if key in st.session_state:
        return st.session_state[key]
    return None


def set_image(key: str, img: Image.Image):
    st.session_state[key] = img


def prompt_and_generate_button(prefix, pipeline_name: PIPELINE_NAMES, **kwargs):
    prompt = st.text_area(
        "Prompt",
        value=DEFAULT_PROMPT,
        key=f"{prefix}-prompt",
    )
    negative_prompt = st.text_area(
        "Negative prompt",
        value=DEFAULT_NEGATIVE_PROMPT,
        key=f"{prefix}-negative-prompt",
    )
    
    col1, col2, col3 = st.columns(3)
    with col1:
        steps = st.slider("Steps", min_value=0, max_value=300, value=100, step=10, key=f"{prefix}-inference-steps")
    with col2:
        guidance_scale = st.slider(
            "Guidance scale", min_value=0.0, max_value=100.0, value=50.0, step=0.5, key=f"{prefix}-guidance-scale"
        )
    with col3:
        strength = st.slider(
            "Strength", min_value=0.3, max_value=0.8, value=0.55, step=0.01, key=f"{prefix}-strength"
        )

    enable_attention_slicing = st.checkbox('어텐션 슬라이싱 활성화(더 높은 해상도를 활성화하지만 더 느림)', key=f"{prefix}-attention-slicing", value=True)
    enable_xformers = st.checkbox('xformers 라이브러리 활성화(더 나은 메모리 사용)', key=f"{prefix}-xformers", value=True)

    if st.button("이미지 출력", key=f"{prefix}-btn"):
        with st.spinner("이미지 출력 중..."):
            image = generate(
                prompt,
                pipeline_name,
                negative_prompt=negative_prompt,
                steps=steps,
                guidance_scale=guidance_scale,
                strength=strength,
                enable_attention_slicing=enable_attention_slicing,
                enable_xformers=enable_xformers,
                **kwargs,
            )
            set_image(OUTPUT_IMAGE_KEY, image.copy())
        st.image(image)


def width_and_height_sliders(prefix):
    col1, col2 = st.columns(2)
    with col1:
        width = st.slider(
            "Width",
            min_value=64,
            max_value=1024,
            step=64,
            value=512,
            key=f"{prefix}-width",
        )
    with col2:
        height = st.slider(
            "Height",
            min_value=64,
            max_value=1024,
            step=64,
            value=512,
            key=f"{prefix}-height",
        )
    return width, height


def image_uploader(prefix):
    image = st.file_uploader("Image", ["jpg", "png", "jpeg"], key=f"{prefix}-uploader")
    if image:
        image = Image.open(image)
        print(f"loaded input image of size ({image.width}, {image.height})")
        image = image.resize((DEFAULT_WIDTH, DEFAULT_HEIGHT))
        return image

    return get_image(LOADED_IMAGE_KEY)


def inpainting():
    image = image_uploader("inpainting")

    if not image:
        return None, None

    brush_size = st.number_input("Brush Size", value=50, min_value=1, max_value=100)

    canvas_result = st_canvas(
        fill_color="rgba(255, 255, 255, 0.0)",
        stroke_width=brush_size,
        stroke_color="#FFFFFF",
        background_color="#000000",
        background_image=image,
        update_streamlit=True,
        height=image.height,
        width=image.width,
        drawing_mode="freedraw",
        # Use repr(image) to force the component to reload when the image
        # changes, i.e. when asking to use the current output image
        key="inpainting",
    )

    if not canvas_result or canvas_result.image_data is None:
        return None, None

    mask = canvas_result.image_data
    mask = mask[:, :, -1] > 0
    if mask.sum() > 0:
        mask = Image.fromarray(mask)
        st.image(mask)
        return image, mask

    return None, None


def txt2img_tab():
    prefix = "txt2img"
    width, height = width_and_height_sliders(prefix)
    prompt_and_generate_button(prefix, "txt2img", width=width, height=height)


def inpainting_tab():
    col1, col2 = st.columns(2)

    with col1:
        image_input, mask_input = inpainting()

    with col2:
        if image_input and mask_input:
            prompt_and_generate_button(
                "inpaint", "inpaint", image_input=image_input, mask_input=mask_input
            )


def img2img_tab():
    col1, col2 = st.columns(2)

    with col1:
        image = image_uploader("img2img")
        if image:
            st.image(image)

    with col2:
        if image:
            prompt_and_generate_button("img2img", "img2img", image_input=image)


def main():
    st.set_page_config(layout="wide")
    st.title("Stable Diffusion v1.5 데모")

    tab1, tab2, tab3 = st.tabs(
        ["Image to image (img2img)", "Inpainting", "Text to Image (txt2img)"]
    )
    with tab1:
        img2img_tab()

    with tab2:
        inpainting_tab()

    with tab3:
        txt2img_tab()

    with st.sidebar:
        st.header("Latest Output Image")
        output_image = get_image(OUTPUT_IMAGE_KEY)
        if output_image:
            st.image(output_image)
            if st.button("Use this image for inpainting and img2img"):
                set_image(LOADED_IMAGE_KEY, output_image.copy())
                st.experimental_rerun()
        else:
            st.markdown("No output generated yet")


if __name__ == "__main__":
    main()
