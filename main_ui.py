import traceback
import streamlit as st
import os
import importlib.util

# ── Page setup FIRST ──────────────────────────
st.set_page_config(
    page_title="Your Tech Tutor",
    page_icon="🤖",
    layout="centered"
)

st.title('Your Tech Buddy')
st.caption("Place to learn everything")
st.divider()

# ── Session state ─────────────────────────────
if "start_error" not in st.session_state:
    st.session_state.start_error = None
if "messages" not in st.session_state:
    st.session_state.messages = []

# ── Initialize agent ──────────────────────────
if "agent" not in st.session_state:
    with st.spinner("Starting TechGuru..."):
        try:
            # ── Step 1: Inject secrets FIRST ──
            # WHY before loading module?
            # azure_services.py reads os.environ when it loads
            # If we inject AFTER loading, values are already None
            print("Injecting secrets...")
            for key in ["AZURE_ENDPOINT", "MODEL_DEPLOYMENT_NAME",
                       "BING_CONNECTION_NAME", "AZURE_API_KEY"]:
                try:
                    value = st.secrets[key]
                    os.environ[key] = value
                    print(f"✅ {key} injected")
                except Exception:
                    print(f"⚠️ {key} not found in secrets")

            # ── Step 2: Load module AFTER secrets injected ──
            current_file  = os.path.abspath(__file__)
            root_dir      = os.path.dirname(current_file)
            src_dir       = os.path.join(root_dir, 'src')
            paths_file    = os.path.join(src_dir, 'paths.py')

            spec  = importlib.util.spec_from_file_location("paths", paths_file)
            paths = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(paths)

            services_file = os.path.join(src_dir, 'services', 'azure_services.py')
            spec2         = importlib.util.spec_from_file_location("azure_services", services_file)
            azure_mod     = importlib.util.module_from_spec(spec2)
            spec2.loader.exec_module(azure_mod)  # ← NOW secrets are in os.environ
            TechAgent     = azure_mod.TechAgent

            # ── Step 3: Create agent ──────────
            st.session_state.agent       = TechAgent()
            st.session_state.start_error = None
            print("✅ TechAgent ready!")

        except Exception as e:
            st.session_state.start_error = traceback.format_exc()
            print(f"❌ Error: {st.session_state.start_error}")

# ── Show error ────────────────────────────────
if st.session_state.get("start_error"):
    st.error("TechGuru failed to start!")
    st.code(st.session_state.start_error)
    st.stop()

if "agent" not in st.session_state:
    st.error("Agent not initialized — please refresh")
    st.stop()

# ── Welcome message ───────────────────────────
if len(st.session_state.messages) == 0:
    with st.chat_message("assistant"):
        st.markdown("""
👋 **Welcome! I'm TechGuru — your personal tech expert.**

🎓 **Teach you any technology** — say *"I want to learn Python"*
🤝 **Help when stuck** — say *"I don't understand decorators"*
📰 **Live tech news** — say *"Latest news on AI"*

> I only talk about **technology and development**!
        """)

# ── Chat history ──────────────────────────────
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ── Chat input ────────────────────────────────
if prompt := st.chat_input("Tell me which technology you want to learn..."):

    if "agent" not in st.session_state:
        st.error("TechGuru not initialized — please refresh")
        st.stop()

    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            Response = st.session_state.agent.chat(prompt)
        st.markdown(Response)
    st.session_state.messages.append({"role": "assistant", "content": Response})