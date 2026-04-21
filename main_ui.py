import streamlit as st
import os 
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.services.azure_services import TechAgent


# page setup
st.set_page_config(
    page_title="Your Tech Tutor",
    page_icon="🤖",
    layout="centered"
)



#Headers
st.title('Your Tech Buddy')
st.caption("Place to learn everything")
st.divider()



#Session State

if "agent" not in st.session_state:
    with st.spinner("Running the agent, Please wait......"):
        try:
            st.session_state.agent = TechAgent()
            st.session_state.start_error = None
        except Exception as e:
            print(f"Some Error Occured: {e}")


if "messages" not in st.session_state:
    st.session_state.messages = []



if len(st.session_state.messages) == 0:
    with st.chat_message("assistant"):
     st.markdown("""
      👋 **Welcome! I'm TechBot — your personal tech expert.**
      
      Here's what I can do for you:
      
      🎓 **Teach you any technology** — just say *"I want to learn Python"*
      
      🤝 **Help when you're stuck** — say *"I don't understand Python decorators"*
      
      📰 **Get live tech news** — say *"Latest news on AI"*
      
      > ⚠️ I only talk about **technology and development**. 
      > Ask me anything tech-related!
    """)
    

#Displaying the History
for message in st.session_state.messages:
    with st.chat_message(message['role']):
        st.markdown(message['content'])



# chat input field
if prompt := st.chat_input("tell me which technology you want to learn..."):

    #show user message immediately
    with st.chat_message("user"):
        st.markdown(prompt)

    
    # save to history
    st.session_state.messages.append({
        "role": "user",
        "content": prompt
    })


    # get and show ai reponse 
    with st.chat_message('assistant'):
        with st.spinner("Thinking"):
            Response = st.session_state.agent.chat(prompt)
        st.markdown(Response)
    

    # save bot response as well
    st.session_state.messages.append({
        'role': "assistant",
        "content" : Response
    })