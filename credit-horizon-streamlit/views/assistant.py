import streamlit as st

from core import advisor, exports, repo, ui

ui.header("✨", "Risk Advisor – Assistant IA",
          "Consultant senior virtuel en gestion des risques financiers et COSO 2013. Il raisonne uniquement sur les données de la plateforme et ne prend aucune décision d'octroi.")
stt = advisor.status()
if stt["provider"] == "anthropic":
    st.success(f"IA générative connectée : Claude ({stt['model']}) via l'API Anthropic – clé conservée côté serveur.")
else:
    st.warning("Aucune clé ANTHROPIC_API_KEY configurée : les réponses sont produites par le moteur d'analyse local à partir des données réelles de la plateforme. "
               "Ajoutez la clé dans les secrets Streamlit pour activer Claude.")

CAPS = [
    ("📋 Analyser le registre", "Analyse l'ensemble du registre des risques : exposition globale, répartition par catégorie, risques critiques et couverture par les contrôles."),
    ("🧮 Expliquer les scores P × G", "Explique les scores P × G de chaque risque du registre, en t'appuyant sur les échelles et les justifications enregistrées."),
    ("🎯 Risques prioritaires", "Identifie les risques prioritaires et justifie l'ordre de traitement, en tenant compte de la chaîne causale entre les risques."),
    ("🏛️ Relier aux principes COSO", "Relie chaque risque du registre aux composantes et principes COSO 2013 concernés, avec l'appréciation actuelle de chaque principe."),
    ("📁 Incohérences documentaires", "Détecte les incohérences documentaires et les pièces manquantes dans les dossiers TPE enregistrés, et indique les risques concernés."),
    ("🛡️ Proposer des contrôles", "Propose des contrôles internes pour renforcer la couverture des risques, en identifiant les risques insuffisamment couverts et les points de dépendance."),
    ("💡 Recommandations", "Génère des recommandations personnalisées pour les risques critiques et élevés, au format RISQUE → LACUNE COSO → ACTION CORRECTIVE → RESPONSABLE → INDICATEUR DE SUIVI."),
    ("📌 Plan d'action", "Construis un plan d'action priorisé (P1, P2, P3) à partir des risques, des recommandations et de l'avancement actuel des actions."),
    ("🐞 Analyser les anomalies", "Analyse le registre des anomalies : tendances, risques et contrôles concernés, anomalies en retard ou à escalader selon la charte."),
    ("📝 Synthèse exécutive", "Rédige une synthèse exécutive professionnelle de la situation des risques et du contrôle interne, destinée à la direction générale."),
    ("📑 Rapport de gestion des risques", "Prépare un rapport de gestion des risques structuré : contexte, cartographie, diagnostic COSO, dispositif de contrôle, anomalies, plan d'action et recommandations."),
]

msgs = st.session_state.setdefault("chat", [])
pending = st.session_state.pop("advisor_prompt", None)

with st.expander("Analyses prêtes à l'emploi", expanded=not msgs):
    cols = st.columns(4)
    for i, (label, prompt) in enumerate(CAPS):
        if cols[i % 4].button(label, use_container_width=True, key=f"cap{i}"):
            pending = prompt

for m in msgs:
    with st.chat_message(m["role"], avatar="🧑‍💼" if m["role"] == "user" else "🛡️"):
        st.markdown(m["content"])

question = st.chat_input("Ex. : Pourquoi R03 est-il le risque le plus critique ? Quels contrôles renforcer pour R07 ?")
question = question or pending
if question:
    msgs.append({"role": "user", "content": question})
    with st.chat_message("user", avatar="🧑‍💼"):
        st.markdown(question)
    with st.chat_message("assistant", avatar="🛡️"):
        answer = st.write_stream(advisor.ask(msgs, repo.snapshot()))
    msgs.append({"role": "assistant", "content": answer})
    ui.audit("Requête IA", "Risk Advisor", stt["provider"], question[:300])

if msgs:
    c1, c2 = st.columns([1, 1])
    last = next((m["content"] for m in reversed(msgs) if m["role"] == "assistant"), "")
    c1.download_button("📄 Exporter la dernière réponse en PDF", exports.markdown_pdf("Risk Advisor – Analyse", last), "risk-advisor.pdf", "application/pdf", use_container_width=True)
    if c2.button("🔄 Nouvelle conversation", use_container_width=True):
        st.session_state.chat = []
        st.rerun()
