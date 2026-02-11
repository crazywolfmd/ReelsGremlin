import streamlit as st
from platforms import youtube, facebook, instagram, tiktok

# ------------------ CONFIG ------------------
st.set_page_config(
    page_title="Content Downloader",
    page_icon="⬇️",
    layout="centered"
)

# ------------------ HEADER ------------------
st.markdown(
    "<h3 style='margin-bottom:0.3rem;'>⬇️ Reels Gremlin tool</h2>",
    unsafe_allow_html=True
)

st.caption("Analyze and download content from major platforms")

st.divider()

# ------------------ PLATFORM SELECTOR ------------------

platforms = {
    "YouTube": youtube,
    "Facebook": facebook,
    "Instagram": instagram,
    "TikTok": tiktok,
}

selected_platform = st.selectbox(
    "Select Platform",
    list(platforms.keys())
)

st.divider()

# ------------------ URL INPUT ------------------

url = st.text_input(
    "Paste Content URL",
    placeholder="https://..."
)

analyze_button = st.button(
    "Analyze Content",
    use_container_width=True
)

# ------------------ ANALYSIS ------------------

if analyze_button and url:

    with st.spinner("Analyzing content..."):
        try:
            result = platforms[selected_platform].analyze(url)

            st.success("Content analyzed successfully")

            # Thumbnail
            if result.get("thumbnail"):
                st.image(result["thumbnail"], use_container_width=True)

            # Title
            st.subheader(result.get("title", "No Title"))

            # Metadata Section
            with st.expander("View Details"):
                st.write("**Description:**")
                st.write(result.get("description", "No description"))

                tags = result.get("tags", [])
                if tags:
                    st.write("**Tags:**")
                    st.write(", ".join(tags))

            st.divider()

            # Download Buttons
            col1, col2 = st.columns(2)

            with col1:
                if result.get("download_video"):
                    st.link_button(
                        "⬇️ Download Video",
                        result["download_video"],
                        use_container_width=True
                    )

            with col2:
                if result.get("download_audio"):
                    st.link_button(
                        "🎵 Download Audio",
                        result["download_audio"],
                        use_container_width=True
                    )

        except Exception as e:
            st.error("Failed to analyze URL.")
            st.exception(e)
