import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage
from agent import agent


st.title("PUCIT GPA & CGPA Advisor")
st.write("Ask any questions about your GPA, CGPA, courses, or degree planning.")


if st.sidebar.button("Clear Chat"):
    st.session_state.messages = []
    st.rerun()


if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    role = "user" if isinstance(msg, HumanMessage) else "assistant"
    with st.chat_message(role):
        st.write(msg.content)

user_input = st.chat_input("Type your message here...")

if user_input:
    
    with st.chat_message("user"):
        st.write(user_input)
    st.session_state.messages.append(HumanMessage(content=user_input))

    
    result = agent.invoke({"messages": st.session_state.messages})

    
    last_message = result["messages"][-1]
    reply = getattr(last_message, "text", None) or last_message.content

    
    with st.chat_message("assistant"):
        st.write(reply)
    st.session_state.messages.append(AIMessage(content=reply))
