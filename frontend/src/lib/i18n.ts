/**
 * UI Localization (i18n) dictionary for Nyayavarta.
 * Full multilingual translations for all supported Indian languages.
 */

export interface UITranslation {
  emergencyTitle: string;
  legalAidText: string;
  tollFree: string;
  police: string;
  cyberCrime: string;
  women: string;
  appTitle: string;
  appSubtitle: string;
  apiOnline: string;
  tabChat: string;
  tabUpload: string;
  tabMatrix: string;
  ragTag: string;
  chatHeader: string;
  chatSubtitle: string;
  chatGreeting: string;
  chatGreetingSub: string;
  suggestedQueriesTitle: string;
  inputPlaceholder: string;
  sendBtn: string;
  listening: string;
  stopSend: string;
  attachDoc: string;
  docAttached: string;
  legalGuidanceHeader: string;
  historyTitle: string;
  newConsultationBtn: string;
  noHistoryTitle: string;
  noHistorySub: string;
  privateHistoryTitle: string;
  privateHistorySub: string;
  loginSignUpBtn: string;
  loadingConsultations: string;
  messagesCount: string;
  privateDataBadge: string;
  hideHistoryBtn: string;
  showHistoryBtn: string;
  clearChatBtn: string;
  userLoginBtn: string;
  userLogOutBtn: string;
  activeThread: string;
  deleteChatBtn: string;
  liveGraphRAG: string;
  privateAndEncrypted: string;
  supportedLangs: string;
  legalAidHelpline: string;
  nalsaPortal: string;
  tollFreeHelpline: string;
  empoweringCitizens: string;
  clearChatConfirm: string;
  deleteChatConfirm: string;
  citationsTitle: string;
  showLess: string;
  showAll: string;
  statute: string;
  transitionNotes: string;
  uploadBannerTag: string;
  uploadBannerTitle: string;
  uploadBannerDesc: string;
  goToChatBtn: string;
  uploadBoxTitle: string;
  uploadBoxDesc: string;
  clickToBrowse: string;
  supportedFormats: string;
  uploadingChunks: string;
  indexedDocsTitle: string;
  filesCount: string;
  noDocsYet: string;
  chunksInNeo4j: string;
  askInChat: string;
  architectureTitle: string;
  architectureDesc: string;
  knowledgeGraphLabel: string;
  keywordRetrievalLabel: string;
  orchestrationLabel: string;
  statutoryGraphDataLabel: string;
  guidelinesTitle: string;
  guideline1: string;
  guideline2: string;
  guideline3: string;
  guideline4: string;
  matrixCorpusTag: string;
  matrixMainTitle: string;
  matrixMainDesc: string;
  transitionsCountLabel: string;
  precedentsCountLabel: string;
  tabStatutoryConcordance: string;
  tabLandmarkPrecedents: string;
  searchStatutesPlaceholder: string;
  searchPrecedentsPlaceholder: string;
  categoryLabel: string;
  catAll: string;
  catBns: string;
  catBnss: string;
  catBsa: string;
  catSpecial: string;
  colSubject: string;
  colOldLaw: string;
  colNewLaw: string;
  colKeyTransition: string;
  colActions: string;
  btnDetails: string;
  btnAskAI: string;
  colCaseTitle: string;
  colIssue: string;
  colHolding: string;
  colApplication: string;
  modalTitle: string;
  modalSubtitle: string;
  oldProvision: string;
  modernProvision: string;
  keyLegalShift: string;
  proceduralNotes: string;
  proceduralClassification: string;
  askInLegalChat: string;
  copied: string;
  close: string;
  suggestedQueries: Array<{ label: string; text: string }>;
}

export const I18N_STRINGS: Record<string, Partial<UITranslation> & Record<string, any>> = {
  en: {
    "emergencyTitle": "Emergency & Aid",
    "legalAidText": "National Legal Aid Helpline (NALSA / DLSA):",
    "tollFree": "15100 (Toll-Free, 24x7)",
    "police": "Police: 112",
    "cyberCrime": "Cyber Crime: 1930",
    "women": "Women: 1091",
    "appTitle": "Nyayavarta",
    "appSubtitle": "Multilingual Legal Assistant for Indian Citizens (IPC → BNS / CrPC → BNSS / BSA)",
    "apiOnline": "API Online",
    "tabChat": "Legal Chat",
    "tabUpload": "Upload Legal Document",
    "tabMatrix": "Law Transition Matrix",
    "ragTag": "GraphRAG + Neo4j",
    "chatHeader": "Nyayavarta AI Assistant",
    "chatSubtitle": "Indian Penal Code (IPC) → Bharatiya Nyaya Sanhita (BNS) & Legal Aid",
    "chatGreeting": "Namaste! How can Nyayavarta assist you today?",
    "chatGreetingSub": "Type in your language, click the mic to speak, or upload your legal document/report. Our GraphRAG maps old laws to new BNS provisions and provides step-by-step aid.",
    "suggestedQueriesTitle": "Suggested Legal Queries",
    "inputPlaceholder": "Type your legal query, attach a PDF report, or click the mic to speak...",
    "sendBtn": "Send",
    "listening": "Listening...",
    "stopSend": "Stop & Send",
    "attachDoc": "Attach Legal Document (PDF / DOCX)",
    "docAttached": "Document attached & indexed",
    "legalGuidanceHeader": "Nyayavarta Legal Guidance",
    "historyTitle": "Consultation History",
    "newConsultationBtn": "+ New Consultation",
    "noHistoryTitle": "No Previous Consultations",
    "noHistorySub": "Ask a legal question to begin a new consultation.",
    "privateHistoryTitle": "Private Consultation History",
    "privateHistorySub": "Log in to securely save and access your past consultations. Your consultations remain private.",
    "loginSignUpBtn": "Log In / Sign Up",
    "loadingConsultations": "Loading consultations...",
    "messagesCount": "messages",
    "privateDataBadge": "Private & Encrypted",
    "hideHistoryBtn": "Hide History",
    "showHistoryBtn": "Show History",
    "clearChatBtn": "Clear",
    "userLoginBtn": "Log In / Account",
    "userLogOutBtn": "Log Out",
    "activeThread": "Active Consultation",
    "deleteChatBtn": "Delete Chat",
    "liveGraphRAG": "Live GraphRAG",
    "privateAndEncrypted": "Private & Encrypted",
    "supportedLangs": "Supported: Automatic Voice Detection, Text & PDF reports in 14 Indian languages",
    "legalAidHelpline": "Legal Aid Toll-Free: 15100",
    "nalsaPortal": "NALSA Official Portal",
    "tollFreeHelpline": "Toll-Free Helpline: 15100",
    "empoweringCitizens": "Empowering Indian Citizens with AI Legal Literacy",
    "clearChatConfirm": "Clear the current legal consultation conversation?",
    "deleteChatConfirm": "Delete this active legal consultation from your history? This action is permanent.",
    "citationsTitle": "Legal Citations & Law Mapping",
    "showLess": "Show Less",
    "showAll": "Show All",
    "statute": "Statute",
    "transitionNotes": "Transition / Notes:",
    "uploadBannerTag": "What is Document Upload?",
    "uploadBannerTitle": "Ask AI Questions Directly About Your Legal Report or FIR Copy",
    "uploadBannerDesc": "When you upload an FIR copy, court petition, agreement, or police report (PDF/DOCX), Nyayavarta parses its text, segments it into searchable chunks, and indexes it into the Neo4j Knowledge Graph. You can then ask questions in the Legal Chat (via text or voice) and the AI will reference your specific document!",
    "goToChatBtn": "Go to Legal Chat",
    "uploadBoxTitle": "Legal Document Ingestion",
    "uploadBoxDesc": "Upload legal filings, FIR copies, petitions, or contracts (PDF, DOCX, TXT up to 20MB). Our PyMuPDF engine extracts and indexes chunks dynamically into your RAG pipeline.",
    "clickToBrowse": "Click to browse or drag and drop files here",
    "supportedFormats": "PDF, Word (.docx) or plain text (.txt)",
    "uploadingChunks": "Extracting text and chunking into Neo4j Knowledge Graph & BM25...",
    "indexedDocsTitle": "Indexed Documents in this Session",
    "filesCount": "file(s)",
    "noDocsYet": "No documents uploaded yet. Upload a PDF or Word file above (or using the paperclip button in the chat) to index its content into the knowledge graph.",
    "chunksInNeo4j": "chunks in Neo4j",
    "askInChat": "Ask in Chat",
    "architectureTitle": "GraphRAG Architecture (Neo4j)",
    "architectureDesc": "Nyayavarta combines Neo4j Knowledge Graph traversal with BM25 keyword search to maximize legal accuracy.",
    "knowledgeGraphLabel": "Knowledge Graph",
    "keywordRetrievalLabel": "Keyword Retrieval",
    "orchestrationLabel": "Orchestration",
    "statutoryGraphDataLabel": "Statutory Graph Data",
    "guidelinesTitle": "Document Guidelines",
    "guideline1": "Supported: FIR copies, court petitions, bail orders, legal contracts.",
    "guideline2": "Text extraction via PyMuPDF with page-level metadata.",
    "guideline3": "Max file size: 20MB.",
    "guideline4": "Indexed chunks are automatically retrieved in subsequent chat queries.",
    "matrixCorpusTag": "Official Indian Criminal Law Concordance & Precedent Corpus",
    "matrixMainTitle": "Indian Law Transition Matrix & Landmark Precedents",
    "matrixMainDesc": "Explore 105 statutory transitions (IPC ↔ BNS, CrPC ↔ BNSS, Evidence Act ↔ BSA, Special Acts) and 38 Landmark Supreme Court Precedents. Click on any provision or case to view complete comparative penalties, procedural classifications, and citizen rights.",
    "transitionsCountLabel": "Transitions",
    "precedentsCountLabel": "SC Precedents",
    "tabStatutoryConcordance": "Statutory Concordance",
    "tabLandmarkPrecedents": "Landmark Precedents",
    "searchStatutesPlaceholder": "Search offense, section (e.g. 420, 302, 173), or penalty...",
    "searchPrecedentsPlaceholder": "Search precedent (e.g. Lalita Kumari, Arnesh Kumar, Bail)...",
    "categoryLabel": "Category:",
    "catAll": "All",
    "catBns": "BNS (Penal)",
    "catBnss": "BNSS (Procedure & Police)",
    "catBsa": "BSA (Evidence & Records)",
    "catSpecial": "Special & Central Acts",
    "colSubject": "Subject / Offence",
    "colOldLaw": "Colonial / Old Law",
    "colNewLaw": "Modern Law (2023 / Special)",
    "colKeyTransition": "Key Statutory Transition & Penalty",
    "colActions": "Actions",
    "btnDetails": "Details",
    "btnAskAI": "Ask AI",
    "colCaseTitle": "Landmark Case & Citation",
    "colIssue": "Legal Issue & Topic",
    "colHolding": "Supreme Court Holding & Ratio",
    "colApplication": "BNS / BNSS Statutory Application",
    "modalTitle": "Statutory Transition Analysis",
    "modalSubtitle": "Colonial Law vs Modern 2023 Enactment",
    "oldProvision": "Old Statutory Provision",
    "modernProvision": "Modern Statutory Provision",
    "keyLegalShift": "Key Legal Shift & Citizen Impact",
    "proceduralNotes": "Procedural & Penalty Notes",
    "proceduralClassification": "Procedural Classification",
    "askInLegalChat": "Ask AI in Legal Chat",
    "copied": "Copied!",
    "close": "Close",
    "suggestedQueries": [
        {
            "label": "FIR / Zero FIR (BNSS 173)",
            "text": "How to file an FIR? Is Zero FIR legally valid under BNSS Section 173?"
        },
        {
            "label": "Cheating (IPC 420 → BNS 318)",
            "text": "What is the difference between old IPC 420 and new BNS 318 for cheating?"
        },
        {
            "label": "Arrest Rights (BNSS 35)",
            "text": "What are the rights of an arrested citizen under BNSS Section 35?"
        },
        {
            "label": "Free Legal Aid (15100)",
            "text": "How can an eligible citizen get free state legal counsel via NALSA 15100 helpline?"
        }
    ]
},

  ta: {
    "emergencyTitle": "அவசர மற்றும் உதவி",
    "legalAidText": "தேசிய சட்ட உதவி ஹெல்ப்லைன் (NALSA / DLSA):",
    "tollFree": "15100 (கட்டணமில்லா, 24x7)",
    "police": "போலீஸ்: 112",
    "cyberCrime": "சைபர் கிரைம்: 1930",
    "women": "பெண்கள்: 1091",
    "appTitle": "நியாயவர்தா",
    "appSubtitle": "இந்திய குடிமக்களுக்கான பன்மொழி சட்ட உதவியாளர் (IPC → BNS / CrPC → BNSS / BSA)",
    "apiOnline": "API ஆன்லைன்",
    "tabChat": "சட்ட அரட்டை",
    "tabUpload": "சட்ட ஆவணத்தைப் பதிவேற்றவும்",
    "tabMatrix": "சட்ட மாற்றம் மேட்ரிக்ஸ்",
    "ragTag": "வரைபடம் + நியோ4ஜே",
    "chatHeader": "நியாயவர்தா AI உதவியாளர்",
    "chatSubtitle": "இந்திய தண்டனைச் சட்டம் (IPC) → பாரதிய நியாய சன்ஹிதா (BNS) & சட்ட உதவி",
    "chatGreeting": "நமஸ்தே! இன்று நியாயவர்தா உங்களுக்கு எப்படி உதவ முடியும்?",
    "chatGreetingSub": "உங்கள் மொழியில் தட்டச்சு செய்யவும், பேச மைக்கைக் கிளிக் செய்யவும் அல்லது உங்கள் சட்ட ஆவணம்/அறிக்கையைப் பதிவேற்றவும். எங்கள் GraphRAG ஆனது பழைய சட்டங்களை புதிய BNS விதிகளுக்கு வரைபடமாக்குகிறது மற்றும் படிப்படியான உதவியை வழங்குகிறது.",
    "suggestedQueriesTitle": "பரிந்துரைக்கப்படும் சட்ட வினாக்கள்",
    "inputPlaceholder": "உங்கள் சட்ட வினவலை உள்ளிடவும், PDF அறிக்கையை இணைக்கவும் அல்லது பேச மைக்கை கிளிக் செய்யவும்...",
    "sendBtn": "அனுப்பு",
    "listening": "கேட்கிறது...",
    "stopSend": "நிறுத்து & அனுப்பு",
    "attachDoc": "சட்ட ஆவணத்தை இணைக்கவும் (PDF / DOCX)",
    "docAttached": "ஆவணம் இணைக்கப்பட்டுள்ளது & அட்டவணைப்படுத்தப்பட்டது",
    "legalGuidanceHeader": "நியாயவர்தா சட்ட வழிகாட்டுதல்",
    "historyTitle": "ஆலோசனை வரலாறு",
    "newConsultationBtn": "+ புதிய ஆலோசனை",
    "noHistoryTitle": "முந்தைய ஆலோசனைகள் இல்லை",
    "noHistorySub": "புதிய ஆலோசனையைத் தொடங்க சட்டக் கேள்வியைக் கேளுங்கள்.",
    "privateHistoryTitle": "தனிப்பட்ட ஆலோசனை வரலாறு",
    "privateHistorySub": "உங்கள் கடந்தகால ஆலோசனைகளைப் பாதுகாப்பாகச் சேமிக்கவும் அணுகவும் உள்நுழையவும். உங்கள் ஆலோசனைகள் தனிப்பட்டதாக இருக்கும்.",
    "loginSignUpBtn": "உள்நுழையவும் / பதிவு செய்யவும்",
    "loadingConsultations": "ஆலோசனைகளை ஏற்றுகிறது...",
    "messagesCount": "செய்திகள்",
    "privateDataBadge": "தனிப்பட்ட & மறைகுறியாக்கப்பட்ட",
    "hideHistoryBtn": "வரலாற்றை மறை",
    "showHistoryBtn": "வரலாற்றைக் காட்டு",
    "clearChatBtn": "தெளிவு",
    "userLoginBtn": "உள்நுழைக / கணக்கு",
    "userLogOutBtn": "வெளியேறு",
    "activeThread": "செயலில் கலந்தாய்வு",
    "deleteChatBtn": "அரட்டையை நீக்கு",
    "liveGraphRAG": "நேரடி வரைபடம்",
    "privateAndEncrypted": "தனிப்பட்ட & மறைகுறியாக்கப்பட்ட",
    "supportedLangs": "ஆதரிக்கப்படும்: தானியங்கி குரல் கண்டறிதல், 14 இந்திய மொழிகளில் உரை & PDF அறிக்கைகள்",
    "legalAidHelpline": "சட்ட உதவி இலவசம்: 15100",
    "nalsaPortal": "NALSA அதிகாரப்பூர்வ போர்டல்",
    "tollFreeHelpline": "கட்டணமில்லா உதவி எண்: 15100",
    "empoweringCitizens": "இந்திய குடிமக்களுக்கு AI சட்ட கல்வியறிவு மூலம் அதிகாரமளித்தல்",
    "clearChatConfirm": "தற்போதைய சட்ட ஆலோசனை உரையாடலை அழிக்கவா?",
    "deleteChatConfirm": "இந்த செயலில் உள்ள சட்ட ஆலோசனையை உங்கள் வரலாற்றிலிருந்து நீக்கவா? இந்த நடவடிக்கை நிரந்தரமானது.",
    "citationsTitle": "சட்ட மேற்கோள்கள் & சட்ட மேப்பிங்",
    "showLess": "குறைவாகக் காட்டு",
    "showAll": "அனைத்தையும் காட்டு",
    "statute": "சட்டம்",
    "transitionNotes": "மாற்றம் / குறிப்புகள்:",
    "uploadBannerTag": "ஆவணப் பதிவேற்றம் என்றால் என்ன?",
    "uploadBannerTitle": "உங்கள் சட்ட அறிக்கை அல்லது FIR நகல் பற்றி நேரடியாக AI கேள்விகளைக் கேளுங்கள்",
    "uploadBannerDesc": "நீங்கள் எஃப்ஐஆர் நகல், நீதிமன்ற மனு, ஒப்பந்தம் அல்லது போலீஸ் அறிக்கை (PDF/DOCX) ஆகியவற்றைப் பதிவேற்றும்போது, ​​Nyayavarta அதன் உரையை அலசி, தேடக்கூடிய பகுதிகளாகப் பிரித்து, அதை Neo4j அறிவு வரைபடத்தில் அட்டவணைப்படுத்துகிறது. நீங்கள் சட்ட அரட்டையில் (உரை அல்லது குரல் வழியாக) கேள்விகளைக் கேட்கலாம் மற்றும் AI உங்கள் குறிப்பிட்ட ஆவணத்தைக் குறிப்பிடும்!",
    "goToChatBtn": "சட்ட அரட்டைக்குச் செல்லவும்",
    "uploadBoxTitle": "சட்ட ஆவண உட்செலுத்துதல்",
    "uploadBoxDesc": "சட்டப்பூர்வ பதிவுகள், FIR நகல்கள், மனுக்கள் அல்லது ஒப்பந்தங்கள் (PDF, DOCX, TXT வரை 20MB வரை) பதிவேற்றவும். எங்கள் PyMuPDF இன்ஜின் உங்கள் RAG பைப்லைனில் மாறும் வகையில் பிரித்தெடுக்கிறது மற்றும் அட்டவணைப்படுத்துகிறது.",
    "clickToBrowse": "இங்கே கோப்புகளை உலாவ அல்லது இழுத்து விட கிளிக் செய்யவும்",
    "supportedFormats": "PDF, Word (.docx) அல்லது எளிய உரை (.txt)",
    "uploadingChunks": "உரையைப் பிரித்தெடுத்து, Neo4j அறிவு வரைபடம் & BM25 ஆக இணைக்கிறது...",
    "indexedDocsTitle": "இந்த அமர்வில் அட்டவணைப்படுத்தப்பட்ட ஆவணங்கள்",
    "filesCount": "கோப்பு(கள்)",
    "noDocsYet": "இதுவரை எந்த ஆவணங்களும் பதிவேற்றப்படவில்லை. ஒரு PDF அல்லது வேர்ட் கோப்பை மேலே பதிவேற்றவும் (அல்லது அரட்டையில் உள்ள காகித கிளிப் பொத்தானைப் பயன்படுத்தி) அதன் உள்ளடக்கத்தை அறிவு வரைபடத்தில் அட்டவணைப்படுத்தவும்.",
    "chunksInNeo4j": "Neo4j இல் உள்ள துண்டுகள்",
    "askInChat": "அரட்டையில் கேளுங்கள்",
    "architectureTitle": "கிராஃப்ராக் கட்டிடக்கலை (Neo4j)",
    "architectureDesc": "Nyayavarta சட்ட துல்லியத்தை அதிகரிக்க, Neo4j அறிவு வரைபடத்தை BM25 முக்கிய தேடலுடன் இணைக்கிறது.",
    "knowledgeGraphLabel": "அறிவு வரைபடம்",
    "keywordRetrievalLabel": "முக்கிய வார்த்தை மீட்டெடுப்பு",
    "orchestrationLabel": "இசைக்குழு",
    "statutoryGraphDataLabel": "சட்டப்பூர்வ வரைபடத் தரவு",
    "guidelinesTitle": "ஆவண வழிகாட்டுதல்கள்",
    "guideline1": "ஆதரிக்கப்படும்: FIR நகல்கள், நீதிமன்ற மனுக்கள், ஜாமீன் உத்தரவுகள், சட்ட ஒப்பந்தங்கள்.",
    "guideline2": "பக்க நிலை மெட்டாடேட்டாவுடன் PyMuPDF வழியாக உரை பிரித்தெடுத்தல்.",
    "guideline3": "அதிகபட்ச கோப்பு அளவு: 20MB.",
    "guideline4": "அடுத்தடுத்த அரட்டை வினவல்களில் அட்டவணைப்படுத்தப்பட்ட துண்டுகள் தானாகவே மீட்டெடுக்கப்படும்.",
    "matrixCorpusTag": "அதிகாரப்பூர்வ இந்திய குற்றவியல் சட்ட ஒத்திசைவு & முன்னோடி கார்பஸ்",
    "matrixMainTitle": "இந்திய சட்ட மாற்றம் அணி & முக்கிய முன்மாதிரிகள்",
    "matrixMainDesc": "105 சட்டரீதியான மாற்றங்கள் (IPC ↔ BNS, CrPC ↔ BNSS, எவிடன்ஸ் சட்டம் ↔ BSA, சிறப்புச் சட்டங்கள்) மற்றும் 38 முக்கிய உச்ச நீதிமன்ற முன்மாதிரிகளை ஆராயுங்கள். முழுமையான ஒப்பீட்டு அபராதங்கள், நடைமுறை வகைப்பாடுகள் மற்றும் குடிமக்கள் உரிமைகளைப் பார்க்க ஏதேனும் விதி அல்லது வழக்கின் மீது கிளிக் செய்யவும்.",
    "transitionsCountLabel": "மாற்றங்கள்",
    "precedentsCountLabel": "SC முன்மாதிரிகள்",
    "tabStatutoryConcordance": "சட்டப்பூர்வ ஒத்திசைவு",
    "tabLandmarkPrecedents": "மைல்கல் முன்மாதிரிகள்",
    "searchStatutesPlaceholder": "தேடல் குற்றம், பிரிவு (எ.கா. 420, 302, 173) அல்லது அபராதம்...",
    "searchPrecedentsPlaceholder": "தேடல் முன்னோடி (எ.கா. லலிதா குமாரி, அர்னேஷ் குமார், ஜாமீன்)...",
    "categoryLabel": "வகை:",
    "catAll": "அனைத்து",
    "catBns": "BNS (தண்டனை)",
    "catBnss": "பிஎன்எஸ்எஸ் (செயல்முறை & போலீஸ்)",
    "catBsa": "BSA (ஆதாரம் & பதிவுகள்)",
    "catSpecial": "சிறப்பு மற்றும் மத்திய சட்டங்கள்",
    "colSubject": "பொருள் / குற்றம்",
    "colOldLaw": "காலனித்துவ / பழைய சட்டம்",
    "colNewLaw": "நவீன சட்டம் (2023 / சிறப்பு)",
    "colKeyTransition": "முக்கிய சட்டப்பூர்வ மாற்றம் & அபராதம்",
    "colActions": "செயல்கள்",
    "btnDetails": "விவரங்கள்",
    "btnAskAI": "AI ஐக் கேளுங்கள்",
    "colCaseTitle": "முக்கிய வழக்கு & மேற்கோள்",
    "colIssue": "சட்டச் சிக்கல் & தலைப்பு",
    "colHolding": "சுப்ரீம் கோர்ட் ஹோல்டிங் & ரேஷியோ",
    "colApplication": "BNS / BNSS சட்டப்பூர்வ விண்ணப்பம்",
    "modalTitle": "சட்டப்பூர்வ மாற்றம் பகுப்பாய்வு",
    "modalSubtitle": "காலனித்துவ சட்டம் vs நவீன 2023 அமலாக்கம்",
    "oldProvision": "பழைய சட்ட ஏற்பாடு",
    "modernProvision": "நவீன சட்ட ஏற்பாடு",
    "keyLegalShift": "முக்கிய சட்ட மாற்றம் & குடிமகன் தாக்கம்",
    "proceduralNotes": "நடைமுறை & அபராதக் குறிப்புகள்",
    "proceduralClassification": "நடைமுறை வகைப்பாடு",
    "askInLegalChat": "சட்ட அரட்டையில் AI ஐக் கேளுங்கள்",
    "copied": "நகலெடுக்கப்பட்டது!",
    "close": "மூடு",
    "suggestedQueries": [
        {
            "label": "ஜீரோ எஃப்.ஐ.ஆர் (BNSS 173)",
            "text": "எஃப்ஐஆர் பதிவு செய்வது எப்படி? ஜீரோ எஃப்ஐஆர் செல்லுபடியாகுமா?"
        },
        {
            "label": "மோசடி (IPC 420 → BNS 318)",
            "text": "பழைய IPC 420 மற்றும் புதிய BNS 318 இடையே உள்ள வேறுபாடு என்ன?"
        },
        {
            "label": "கைது உரிமைகள் (BNSS 35)",
            "text": "BNSS பிரிவு 35 இன் கீழ் கைது செய்யப்படும் போது குடிமக்களின் உரிமைகள் யாவை?"
        },
        {
            "label": "இலவச சட்ட உதவி (15100)",
            "text": "நல்சா (NALSA) 15100 உதவி எண் மூலம் இலவச சட்ட உதவி பெறுவது எப்படி?"
        }
    ]
},

  hi: {
    "emergencyTitle": "आपातकालीन एवं सहायता",
    "legalAidText": "राष्ट्रीय कानूनी सहायता हेल्पलाइन (एनएएलएसए/डीएलएसए):",
    "tollFree": "15100 (टोल-फ्री, 24x7)",
    "police": "पुलिस: 112",
    "cyberCrime": "साइबर अपराध: 1930",
    "women": "महिला: 1091",
    "appTitle": "न्यायवार्ता",
    "appSubtitle": "भारतीय नागरिकों के लिए बहुभाषी कानूनी सहायक (आईपीसी → बीएनएस / सीआरपीसी → बीएनएसएस / बीएसए)",
    "apiOnline": "एपीआई ऑनलाइन",
    "tabChat": "कानूनी चैट",
    "tabUpload": "कानूनी दस्तावेज़ अपलोड करें",
    "tabMatrix": "कानून संक्रमण मैट्रिक्स",
    "ragTag": "ग्राफ्रैग + Neo4j",
    "chatHeader": "न्यायवार्ता एआई असिस्टेंट",
    "chatSubtitle": "भारतीय दंड संहिता (आईपीसी) → भारतीय न्याय संहिता (बीएनएस) और कानूनी सहायता",
    "chatGreeting": "नमस्ते! आज न्यायवार्ता आपकी कैसे सहायता कर सकता है?",
    "chatGreetingSub": "अपनी भाषा टाइप करें, बोलने के लिए माइक पर क्लिक करें, या अपना कानूनी दस्तावेज़/रिपोर्ट अपलोड करें। हमारा ग्राफआरएजी पुराने कानूनों को नए बीएनएस प्रावधानों में मैप करता है और चरण-दर-चरण सहायता प्रदान करता है।",
    "suggestedQueriesTitle": "सुझाए गए कानूनी प्रश्न",
    "inputPlaceholder": "अपनी कानूनी क्वेरी टाइप करें, एक पीडीएफ रिपोर्ट संलग्न करें, या बोलने के लिए माइक पर क्लिक करें...",
    "sendBtn": "भेजना",
    "listening": "सुनना...",
    "stopSend": "रोकें और भेजें",
    "attachDoc": "कानूनी दस्तावेज़ संलग्न करें (पीडीएफ/डीओसीएक्स)",
    "docAttached": "दस्तावेज़ संलग्न एवं अनुक्रमित",
    "legalGuidanceHeader": "न्यायवार्ता कानूनी मार्गदर्शन",
    "historyTitle": "परामर्श इतिहास",
    "newConsultationBtn": "+ नया परामर्श",
    "noHistoryTitle": "कोई पिछला परामर्श नहीं",
    "noHistorySub": "नया परामर्श शुरू करने के लिए कानूनी प्रश्न पूछें।",
    "privateHistoryTitle": "निजी परामर्श इतिहास",
    "privateHistorySub": "अपने पिछले परामर्शों को सुरक्षित रूप से सहेजने और उन तक पहुंचने के लिए लॉग इन करें। आपके परामर्श निजी रहते हैं.",
    "loginSignUpBtn": "लॉगइन साइनअप",
    "loadingConsultations": "परामर्श लोड हो रहा है...",
    "messagesCount": "संदेशों",
    "privateDataBadge": "निजी एवं एन्क्रिप्टेड",
    "hideHistoryBtn": "इतिहास छिपाएँ",
    "showHistoryBtn": "इतिहास दिखाएँ",
    "clearChatBtn": "स्पष्ट",
    "userLoginBtn": "लॉगिन खाता",
    "userLogOutBtn": "लॉग आउट",
    "activeThread": "सक्रिय परामर्श",
    "deleteChatBtn": "चैट हटाएँ",
    "liveGraphRAG": "लाइव ग्राफ़आरएजी",
    "privateAndEncrypted": "निजी एवं एन्क्रिप्टेड",
    "supportedLangs": "समर्थित: 14 भारतीय भाषाओं में स्वचालित वॉयस डिटेक्शन, टेक्स्ट और पीडीएफ रिपोर्ट",
    "legalAidHelpline": "कानूनी सहायता टोल-फ्री: 15100",
    "nalsaPortal": "नालसा आधिकारिक पोर्टल",
    "tollFreeHelpline": "टोल-फ्री हेल्पलाइन: 15100",
    "empoweringCitizens": "एआई कानूनी साक्षरता के साथ भारतीय नागरिकों को सशक्त बनाना",
    "clearChatConfirm": "वर्तमान कानूनी परामर्श वार्तालाप साफ़ करें?",
    "deleteChatConfirm": "इस सक्रिय कानूनी परामर्श को अपने इतिहास से हटा दें? यह क्रिया स्थायी है.",
    "citationsTitle": "कानूनी उद्धरण और कानून मानचित्रण",
    "showLess": "कम दिखाएँ",
    "showAll": "सब दिखाएं",
    "statute": "क़ानून",
    "transitionNotes": "संक्रमण/नोट्स:",
    "uploadBannerTag": "दस्तावेज़ अपलोड क्या है?",
    "uploadBannerTitle": "अपनी कानूनी रिपोर्ट या एफआईआर कॉपी के बारे में सीधे एआई प्रश्न पूछें",
    "uploadBannerDesc": "जब आप एक एफआईआर कॉपी, अदालत की याचिका, समझौते, या पुलिस रिपोर्ट (पीडीएफ/डीओसीएक्स) अपलोड करते हैं, तो न्यायवार्ता इसके पाठ को पार्स करता है, इसे खोजने योग्य टुकड़ों में विभाजित करता है, और इसे Neo4j नॉलेज ग्राफ में अनुक्रमित करता है। फिर आप कानूनी चैट में (पाठ या आवाज के माध्यम से) प्रश्न पूछ सकते हैं और एआई आपके विशिष्ट दस्तावेज़ का संदर्भ देगा!",
    "goToChatBtn": "लीगल चैट पर जाएं",
    "uploadBoxTitle": "कानूनी दस्तावेज़ अंतर्ग्रहण",
    "uploadBoxDesc": "कानूनी फाइलिंग, एफआईआर प्रतियां, याचिकाएं, या अनुबंध (पीडीएफ, डीओसीएक्स, टीएक्सटी 20 एमबी तक) अपलोड करें। हमारा PyMuPDF इंजन आपके RAG पाइपलाइन में टुकड़ों को गतिशील रूप से निकालता और अनुक्रमित करता है।",
    "clickToBrowse": "फ़ाइलों को ब्राउज़ करने या खींचने और छोड़ने के लिए यहां क्लिक करें",
    "supportedFormats": "पीडीएफ, वर्ड (.docx) या सादा पाठ (.txt)",
    "uploadingChunks": "टेक्स्ट निकालना और Neo4j नॉलेज ग्राफ़ और BM25 में विभाजित करना...",
    "indexedDocsTitle": "इस सत्र में अनुक्रमित दस्तावेज़",
    "filesCount": "फ़ाइल",
    "noDocsYet": "अभी तक कोई दस्तावेज़ अपलोड नहीं किया गया. इसकी सामग्री को ज्ञान ग्राफ़ में अनुक्रमित करने के लिए ऊपर एक पीडीएफ या वर्ड फ़ाइल अपलोड करें (या चैट में पेपरक्लिप बटन का उपयोग करें)।",
    "chunksInNeo4j": "Neo4j में टुकड़े",
    "askInChat": "चैट में पूछें",
    "architectureTitle": "ग्राफआरएजी आर्किटेक्चर (Neo4j)",
    "architectureDesc": "न्यायवार्ता कानूनी सटीकता को अधिकतम करने के लिए Neo4j नॉलेज ग्राफ़ ट्रैवर्सल को BM25 कीवर्ड खोज के साथ जोड़ती है।",
    "knowledgeGraphLabel": "ज्ञान ग्राफ",
    "keywordRetrievalLabel": "कीवर्ड पुनर्प्राप्ति",
    "orchestrationLabel": "वाद्य-स्थान",
    "statutoryGraphDataLabel": "वैधानिक ग्राफ़ डेटा",
    "guidelinesTitle": "दस्तावेज़ दिशानिर्देश",
    "guideline1": "समर्थित: एफआईआर प्रतियां, अदालत याचिकाएं, जमानत आदेश, कानूनी अनुबंध।",
    "guideline2": "पृष्ठ-स्तरीय मेटाडेटा के साथ PyMuPDF के माध्यम से पाठ निष्कर्षण।",
    "guideline3": "अधिकतम फ़ाइल आकार: 20MB.",
    "guideline4": "अनुक्रमित भाग बाद की चैट क्वेरी में स्वचालित रूप से पुनर्प्राप्त हो जाते हैं।",
    "matrixCorpusTag": "आधिकारिक भारतीय आपराधिक कानून सहमति और मिसाल कॉर्पस",
    "matrixMainTitle": "भारतीय कानून संक्रमण मैट्रिक्स और ऐतिहासिक मिसालें",
    "matrixMainDesc": "105 वैधानिक परिवर्तन (आईपीसी ↔ बीएनएस, सीआरपीसी ↔ बीएनएसएस, साक्ष्य अधिनियम ↔ बीएसए, विशेष अधिनियम) और 38 ऐतिहासिक सुप्रीम कोर्ट मिसालें देखें। संपूर्ण तुलनात्मक दंड, प्रक्रियात्मक वर्गीकरण और नागरिक अधिकार देखने के लिए किसी भी प्रावधान या मामले पर क्लिक करें।",
    "transitionsCountLabel": "बदलाव",
    "precedentsCountLabel": "एससी मिसालें",
    "tabStatutoryConcordance": "वैधानिक सहमति",
    "tabLandmarkPrecedents": "ऐतिहासिक मिसालें",
    "searchStatutesPlaceholder": "तलाशी अपराध, धारा (जैसे 420, 302, 173), या जुर्माना...",
    "searchPrecedentsPlaceholder": "उदाहरण खोजें (जैसे ललिता कुमारी, अर्नेश कुमार, जमानत)...",
    "categoryLabel": "वर्ग:",
    "catAll": "सभी",
    "catBns": "बीएनएस (दंड)",
    "catBnss": "बीएनएसएस (प्रक्रिया एवं पुलिस)",
    "catBsa": "बीएसए (साक्ष्य एवं अभिलेख)",
    "catSpecial": "विशेष एवं केंद्रीय अधिनियम",
    "colSubject": "विषय/अपराध",
    "colOldLaw": "औपनिवेशिक/पुराना कानून",
    "colNewLaw": "आधुनिक कानून (2023/विशेष)",
    "colKeyTransition": "मुख्य वैधानिक परिवर्तन और जुर्माना",
    "colActions": "कार्रवाई",
    "btnDetails": "विवरण",
    "btnAskAI": "एआई से पूछें",
    "colCaseTitle": "ऐतिहासिक मामला और उद्धरण",
    "colIssue": "कानूनी मुद्दा और विषय",
    "colHolding": "सुप्रीम कोर्ट होल्डिंग और अनुपात",
    "colApplication": "बीएनएस/बीएनएसएस वैधानिक आवेदन",
    "modalTitle": "वैधानिक संक्रमण विश्लेषण",
    "modalSubtitle": "औपनिवेशिक कानून बनाम आधुनिक 2023 अधिनियम",
    "oldProvision": "पुराना वैधानिक प्रावधान",
    "modernProvision": "आधुनिक वैधानिक प्रावधान",
    "keyLegalShift": "मुख्य कानूनी बदलाव और नागरिक प्रभाव",
    "proceduralNotes": "प्रक्रियात्मक एवं दंड संबंधी टिप्पणियाँ",
    "proceduralClassification": "प्रक्रियात्मक वर्गीकरण",
    "askInLegalChat": "कानूनी चैट में एआई से पूछें",
    "copied": "नकल की गई!",
    "close": "बंद करना",
    "suggestedQueries": [
        {
            "label": "जीरो एफआईआर (BNSS 173)",
            "text": "एफआईआर (FIR) कैसे दर्ज कराएं? क्या Zero FIR मान्य है?"
        },
        {
            "label": "धोखाधड़ी (IPC 420 → BNS 318)",
            "text": "पुराने IPC 420 और नए BNS 318 (धोखाधड़ी) में क्या अंतर है?"
        },
        {
            "label": "गिरफ्तारी अधिकार (BNSS 35)",
            "text": "BNSS धारा 35 के तहत गिरफ्तारी के समय नागरिक के क्या अधिकार हैं?"
        },
        {
            "label": "मुफ्त कानूनी सहायता (NALSA 15100)",
            "text": "वरिष्ठ नागरिकों के लिए मुफ्त कानूनी सहायता और 15100 हेल्पलाइन की जानकारी दें।"
        }
    ]
}
};

export function getUITranslations(langCode: string): UITranslation {
  const code = (langCode || 'hi').toLowerCase().trim();
  const base = I18N_STRINGS[code] || I18N_STRINGS['hi'] || I18N_STRINGS['en'];
  const defaults = I18N_STRINGS['en'];
  return ({
    ...defaults,
    ...base,
  } as unknown) as UITranslation;
}
