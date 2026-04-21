# import streamlit as st
# import os 
# import sys


# #from src.services.azure_services import TechAgent
# import importlib.util
# # ── Fix import path before anything else ──────
# # WHY at the very top before other imports?
# # Python resolves imports in order.
# # We must fix the path BEFORE importing TechAgent.

# current_file = os.path.abspath(__file__)
# root_dir     = os.path.dirname(current_file)      # techguru-chatbot/
# src_dir      = os.path.join(root_dir, 'src')      # techguru-chatbot/src/
# paths_file   = os.path.join(src_dir, 'paths.py')  # techguru-chatbot/src/paths.py

# # Load paths.py
# spec  = importlib.util.spec_from_file_location("paths", paths_file)
# paths = importlib.util.module_from_spec(spec)
# spec.loader.exec_module(paths)

# # Load azure_services.py directly
# services_file = os.path.join(src_dir, 'services', 'azure_services.py')
# spec2         = importlib.util.spec_from_file_location("azure_services", services_file)
# azure_mod     = importlib.util.module_from_spec(spec2)
# spec2.loader.exec_module(azure_mod)

# # Get TechAgent from loaded module
# TechAgent = azure_mod.TechAgent
# # page setup
# st.set_page_config(
#     page_title="Your Tech Tutor",
#     page_icon="🤖",
#     layout="centered"
# )



# #Headers
# st.title('Your Tech Buddy')
# st.caption("Place to learn everything")
# st.divider()



# #Session State

# if "agent" not in st.session_state:
#     with st.spinner("Running the agent, Please wait......"):
#         try:
#             st.session_state.agent = TechAgent()
#             st.session_state.start_error = None
#         except Exception as e:
#             print(f"Some Error Occured: {e}")


# if "messages" not in st.session_state:
#     st.session_state.messages = []



# if len(st.session_state.messages) == 0:
#     with st.chat_message("assistant"):
#      st.markdown("""
#       👋 **Welcome! I'm TechBot — your personal tech expert.**
      
#       Here's what I can do for you:
      
#       🎓 **Teach you any technology** — just say *"I want to learn Python"*
      
#       🤝 **Help when you're stuck** — say *"I don't understand Python decorators"*
      
#       📰 **Get live tech news** — say *"Latest news on AI"*
      
#       > ⚠️ I only talk about **technology and development**. 
#       > Ask me anything tech-related!
#     """)
    

# #Displaying the History
# for message in st.session_state.messages:
#     with st.chat_message(message['role']):
#         st.markdown(message['content'])



# # chat input field
# if prompt := st.chat_input("tell me which technology you want to learn..."):

#     if 'agent' not in st.session_state:
#         st.error('TechGure is not initialized please refresh the page')
#         st.info()
#         st.stop()
#     #show user message immediately
#     with st.chat_message("user"):
#         st.markdown(prompt)

#     # save to history
#     st.session_state.messages.append({
#         "role": "user",
#         "content": prompt
#     })


#     # get and show ai reponse 
#     with st.chat_message('assistant'):
#         with st.spinner("Thinking"):
#             Response = st.session_state.agent.chat(prompt)
#         st.markdown(Response)
    

#     # save bot response as well
#     st.session_state.messages.append({
#         'role': "assistant",
#         "content" : Response
#     })





import os
import sys
import importlib.util
import traceback
import streamlit as st

# ── Load paths ────────────────────────────────
current_file = os.path.abspath(__file__)
root_dir     = os.path.dirname(current_file)
src_dir      = os.path.join(root_dir, 'src')
paths_file   = os.path.join(src_dir, 'paths.py')

spec  = importlib.util.spec_from_file_location("paths", paths_file)
paths = importlib.util.module_from_spec(spec)
spec.loader.exec_module(paths)

# ── Load TechAgent ────────────────────────────
services_file = os.path.join(src_dir, 'services', 'azure_services.py')
spec2         = importlib.util.spec_from_file_location("azure_services", services_file)
azure_mod     = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(azure_mod)
TechAgent = azure_mod.TechAgent

# ── Page setup ────────────────────────────────
st.set_page_config(page_title="TechGuru", page_icon="🤖", layout="centered")
st.title("🤖 TechGuru")
st.divider()

# ── Initialize session state flags ───────────
if "initialized" not in st.session_state:
    st.session_state.initialized  = False
if "start_error" not in st.session_state:
    st.session_state.start_error  = None
if "messages" not in st.session_state:
    st.session_state.messages     = []

# ── Initialize agent ONCE ────────────────────
if not st.session_state.initialized:
    with st.spinner("Starting TechGuru..."):
        try:
            st.session_state.agent       = TechAgent()
            st.session_state.initialized = True
            st.session_state.start_error = None
        except Exception as e:
            st.session_state.initialized = True
            st.session_state.start_error = traceback.format_exc()

# ── Show error on screen if startup failed ────
if st.session_state.start_error:
    st.error("TechGuru failed to start — here is the exact error:")
    st.code(st.session_state.start_error)  # ← shows full error on screen
    st.stop()

# ── Welcome message ───────────────────────────
if len(st.session_state.messages) == 0:
    with st.chat_message("assistant"):
        st.markdown("""
👋 **Welcome! I am TechGuru — your personal tech expert.**

🎓 **Learn** — *"I want to learn Python"*
🤝 **Get unstuck** — *"I don't understand decorators"*
📰 **Live news** — *"Latest news on AI"*
        """)

# ── Chat history ──────────────────────────────
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ── Ch