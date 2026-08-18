# Documentation & Learning — YES AI CAN
# Learning resources and documentation

import streamlit as st
from pathlib import Path
from services.ui.utils.page_template import page_chrome

st.set_page_config(
    page_title="Documentation & Learning — YES AI CAN",
    layout="wide"
)


# Page header
page_chrome("documentation_learning", "Getting Started",
            "How to get started, plus resources and answers.")
st.markdown("**YES AI CAN — our Community's Lab**")
st.markdown("---")

# Guides removed: every step it described now lives on the page that does the
# thing, and a second copy here drifted out of date the moment a page moved.
tab1, tab3, tab4 = st.tabs(["🚀 Getting Started", "📚 Resources", "❓ FAQs"])

with tab1:
    st.subheader("Getting Started with YES AI CAN")

    # Destinations are named as they appear in the sidebar today. The old text
    # pointed at "Human Stack Directory" and "Agent Library", neither of which
    # is what the rail says any more, so the steps could not be followed.
    st.markdown("""
    ### Welcome to YES AI CAN!

    **YES AI CAN** is our Community's internal AI innovation ecosystem. Here's how to get started:

    #### Step 1: Create Your Profile
    1. Navigate to **👤 People & Skills**
    2. Click **➕ Create/Edit Profile**
    3. Fill in your information:
       - Name, Department, Team, Role
       - Skills and domain expertise
       - Resume upload
       - Portfolio/GitHub links
    4. Save your profile

    #### Step 2: Submit Your Painpoint
    1. Go to **📍 Submit My PainPoints**
    2. List what is slow, manual, repetitive or error-prone — one line each
    3. Say where your task sits on **My Company Workflows**
    4. Pick the outcomes that matter and submit

    #### Step 3: Help Someone Else
    1. Open **🚩 Current Submitted PainPoints**
    2. Find one still marked *Open — needs a helper*
    3. Press **🤝 I can help**, or go to **💡 Propose a Cure**
    4. Describe what your solution does, how, and which AI tools it uses

    #### Step 4: Build and Publish
    1. Track progress on **🔀 Current Challenge Pipeline**
    2. Draft the POC from its ontology blueprint on **🧪 Current POC**
    3. Tick off the acceptance criteria as you prove it
    4. Publish it to the **🤖 Community Agent Library**, where the next matching
       painpoint can reuse it
    """)
with tab3:
    st.subheader("Learning Resources")
    
    st.markdown("""
    ### 📚 Internal Resources
    
    - **AI Ambassador Program**: Join to advance your AI journey
    - **Customer ZERO Agent Library**: Reusable agents for internal use
    - **Pattern Library**: Reusable AI design patterns
    - **Project Showcase**: See what other Rackers have built
    
    ### 🔗 External Resources
    
    - **OpenStack AI Documentation**: Coming soon
    - **Private AI Best Practices**: Coming soon
    - **Explainable AI Guidelines**: Coming soon
    
    ### 🎓 Training & Workshops
    
    - **AI Ambassador Monthly Meetup**: First Tuesday of each month
    - **YES AI CAN Workshop Series**: Every other Thursday
    - **Customer ZERO → Customer ONE Showcase**: Quarterly
    """)

with tab4:
    st.subheader("Frequently Asked Questions")
    
    with st.expander("What is YES AI CAN?"):
        st.write("""
        YES AI CAN is our Community's internal AI innovation ecosystem, built to map our global AI skills, 
        showcase AI projects, provide zero-code tools for building agents, and accelerate reuse through 
        a shared Customer ZERO agent library.
        """)
    
    with st.expander("Who can use YES AI CAN?"):
        st.write("""
        All Rackers! Whether you're technical or not, YES AI CAN gives you the tools to step into AI 
        safely, transparently, and with full support.
        """)
    
    with st.expander("How do I become an AI Ambassador?"):
        st.write("""
        Visit the **🌍 Community & Ambassadors** page and click "Apply to Ambassador Program". 
        Ambassadors help drive AI innovation across our Community.
        """)
    
    with st.expander("What is Customer ZERO vs Customer ONE?"):
        st.write("""
        - **Customer ZERO**: Internal agents and prototypes built by Rackers for internal use
        - **Customer ONE**: Production-ready agents that can be deployed to customers
        The Agent Library helps you move agents from ZERO to ONE.
        """)
    
    with st.expander("How do I submit a project?"):
        st.write("""
        Go to **🧱 Project Hub** → **➕ Submit Project** and fill in the project details form. 
        Include What/So What/For Who/How/Where/What Now/What Next sections.
        """)
    
    with st.expander("Can I use existing agents in my projects?"):
        st.write("""
        Yes! Browse the **🤖 Agent Library** to find reusable agents. You can launch them in the sandbox, 
        test them, and provide feedback. Customer READY agents can be published to Customer ONE.
        """)

# Footer
st.markdown("---")
st.markdown("""
    <div style="text-align: center; color: #64748b; padding: 2rem;">
        💎 YES AI CAN — Rackers Lab & Community | Made with ❤️ by Rackers
    </div>
""", unsafe_allow_html=True)
