/**
 * UI Localization (i18n) dictionary for Nyayavarta.
 * Full multilingual translations for all 14 supported Indian languages.
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
  suggestedQueries: Array<{ label: string; text: string }>;
  inputPlaceholder: string;
  sendBtn: string;
  listening: string;
  stopSend: string;
  attachDoc: string;
  docAttached: string;
  matrixTitle: string;
  matrixSubtitle: string;
  matrixHeaders: {
    crime: string;
    oldLaw: string;
    newLaw: string;
    note: string;
  };
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
}

export const I18N_STRINGS: Record<string, Partial<UITranslation> & Record<string, any>> = {
  // 1. HINDI
  hi: {
    emergencyTitle: 'आपातकालीन एवं सहायता',
    legalAidText: 'राष्ट्रीय विधिक सेवा प्राधिकरण हेल्पलाइन (NALSA / DLSA):',
    tollFree: '15100 (निशुल्क, 24x7)',
    police: 'पुलिस: 112',
    cyberCrime: 'साइबर अपराध: 1930',
    women: 'महिला हेल्पलाइन: 1091',
    appTitle: 'न्यायवार्ता',
    appSubtitle: 'भारतीय नागरिकों के लिए बहुभाषी कानूनी सहायक (IPC → BNS / CrPC → BNSS / BSA)',
    apiOnline: 'सक्रिय (Online)',
    tabChat: 'कानूनी परामर्श (Legal Chat)',
    tabUpload: 'दस्तावेज़ / रिपोर्ट जोड़ें (Upload Document)',
    tabMatrix: 'कानून परिवर्तन चार्ट (Law Matrix)',
    ragTag: 'GraphRAG + Neo4j',
    chatHeader: 'न्यायवार्ता AI कानूनी सहायक',
    chatSubtitle: 'भारतीय दंड संहिता (IPC) → भारतीय न्याय संहिता (BNS) एवं विधिक सहायता',
    chatGreeting: 'नमस्ते! न्यायवार्ता आज आपकी क्या सहायता कर सकता है?',
    chatGreetingSub: 'अपनी भाषा में लिखें, बोलें या अपनी कानूनी रिपोर्ट/एफआईआर अपलोड करें। हमारा नॉलेज ग्राफ आपको सटीक कानूनी प्रावधान व सहायता प्रदान करेगा।',
    suggestedQueriesTitle: 'सुझाए गए कानूनी प्रश्न (Suggested Legal Queries)',
    suggestedQueries: [
      {
        label: 'जीरो एफआईआर (BNSS 173)',
        text: 'एफआईआर (FIR) कैसे दर्ज कराएं? क्या Zero FIR मान्य है?',
      },
      {
        label: 'धोखाधड़ी (IPC 420 → BNS 318)',
        text: 'पुराने IPC 420 और नए BNS 318 (धोखाधड़ी) में क्या अंतर है?',
      },
      {
        label: 'गिरफ्तारी अधिकार (BNSS 35)',
        text: 'BNSS धारा 35 के तहत गिरफ्तारी के समय नागरिक के क्या अधिकार हैं?',
      },
      {
        label: 'मुफ्त कानूनी सहायता (NALSA 15100)',
        text: 'वरिष्ठ नागरिकों के लिए मुफ्त कानूनी सहायता और 15100 हेल्पलाइन की जानकारी दें।',
      },
    ],
    inputPlaceholder: 'अपना कानूनी प्रश्न लिखें या बोलने के लिए माइक दबाएं...',
    sendBtn: 'भेजें (Send)',
    listening: 'ध्वनि सुनी जा रही है...',
    stopSend: 'रोकें और भेजें',
    attachDoc: 'दस्तावेज़ संलग्न करें (PDF / DOCX)',
    docAttached: 'दस्तावेज़ इंडेक्स हो गया',
    matrixTitle: 'प्रमुख आपराधिक कानून परिवर्तन (IPC → BNS / CrPC → BNSS / IEA → BSA)',
    matrixSubtitle: '1 जुलाई 2024 से लागू नए आपराधिक कानूनों के प्रमुख धारा परिवर्तन:',
    matrixHeaders: {
      crime: 'अपराध / विषय',
      oldLaw: 'पुराना कानून (Old Section)',
      newLaw: 'नया कानून 2023 (New Section)',
      note: 'प्रमुख बदलाव / टिप्पणी',
    },
    historyTitle: 'परामर्श इतिहास (History)',
    newConsultationBtn: '+ नया परामर्श (+ New Consultation)',
    noHistoryTitle: 'कोई पुराना परामर्श नहीं',
    noHistorySub: 'कानूनी प्रश्न पूछकर नया परामर्श शुरू करें।',
    privateHistoryTitle: 'निजी परामर्श इतिहास',
    privateHistorySub: 'अपने कानूनी परामर्श को सुरक्षित सहेजने और बाद में देखने के लिए लॉग इन करें। आपका डेटा पूरी तरह निजी है।',
    loginSignUpBtn: 'लॉग इन / साइन अप (Log In)',
    loadingConsultations: 'परामर्श लोड हो रहे हैं...',
    messagesCount: 'संदेश',
    privateDataBadge: 'निजी डेटा सुरक्षित',
    hideHistoryBtn: 'परामर्श छुपाएं',
    showHistoryBtn: 'परामर्श इतिहास',
    clearChatBtn: 'हटाएं (Clear)',
    userLoginBtn: 'लॉग इन / खाता',
    userLogOutBtn: 'लॉग आउट',
  },

  // 2. ENGLISH
  en: {
    emergencyTitle: 'Emergency & Aid',
    legalAidText: 'National Legal Aid Helpline (NALSA / DLSA):',
    tollFree: '15100 (Toll-Free, 24x7)',
    police: 'Police: 112',
    cyberCrime: 'Cyber Crime: 1930',
    women: 'Women: 1091',
    appTitle: 'Nyayavarta',
    appSubtitle: 'Multilingual Legal Assistant for Indian Citizens (IPC → BNS / CrPC → BNSS / BSA)',
    apiOnline: 'API Online',
    tabChat: 'Legal Chat',
    tabUpload: 'Upload Legal Document',
    tabMatrix: 'Law Transition Matrix',
    ragTag: 'GraphRAG + Neo4j',
    chatHeader: 'Nyayavarta AI Assistant',
    chatSubtitle: 'Indian Penal Code (IPC) → Bharatiya Nyaya Sanhita (BNS) & Legal Aid',
    chatGreeting: 'Namaste! How can Nyayavarta assist you today?',
    chatGreetingSub: 'Type in your language, click the mic to speak, or upload your legal document/report. Our GraphRAG maps old laws to new BNS provisions and provides step-by-step aid.',
    suggestedQueriesTitle: 'Suggested Legal Queries',
    suggestedQueries: [
      {
        label: 'FIR / Zero FIR (BNSS 173)',
        text: 'How to file an FIR? Is Zero FIR legally valid under BNSS Section 173?',
      },
      {
        label: 'Cheating (IPC 420 → BNS 318)',
        text: 'What is the difference between IPC 420 and the new BNS 318 for cheating?',
      },
      {
        label: 'Arrest Rights (BNSS 35)',
        text: 'What are my rights upon arrest under BNSS Section 35?',
      },
      {
        label: 'Free Legal Aid (NALSA 15100)',
        text: 'How can citizens get free legal aid from DLSA / NALSA Helpline 15100?',
      },
    ],
    inputPlaceholder: 'Type your legal query, attach a PDF report, or click the mic to speak...',
    sendBtn: 'Send',
    listening: 'Listening to your voice...',
    stopSend: 'Stop & Send',
    attachDoc: 'Attach Legal Document (PDF / DOCX)',
    docAttached: 'Document Indexed in Neo4j',
    matrixTitle: 'Key Criminal Law Transitions (IPC → BNS / CrPC → BNSS / IEA → BSA)',
    matrixSubtitle: 'Effective July 1, 2024, Indian criminal law transitioned to modernized statutes:',
    matrixHeaders: {
      crime: 'Subject / Crime',
      oldLaw: 'Old Law Section',
      newLaw: 'New Law Section (2023)',
      note: 'Key Transition Note',
    },
    historyTitle: 'Consultation History',
    newConsultationBtn: '+ New Consultation',
    noHistoryTitle: 'No previous consultations',
    noHistorySub: 'Ask a legal question to begin a consultation.',
    privateHistoryTitle: 'Private Legal Consultations',
    privateHistorySub: 'Log in or sign up to securely save your consultation history. Your data is isolated and completely private.',
    loginSignUpBtn: 'Log In / Sign Up',
    loadingConsultations: 'Loading consultations...',
    messagesCount: 'messages',
    privateDataBadge: 'Private & Encrypted',
    hideHistoryBtn: 'Hide History',
    showHistoryBtn: 'History',
    clearChatBtn: 'Clear',
    userLoginBtn: 'Log In / Sign Up',
    userLogOutBtn: 'Log Out',
  },

  // 3. MARATHI (मराठी)
  mr: {
    emergencyTitle: 'तातडीची मदत व सहाय्य',
    legalAidText: 'राष्ट्रीय विधी सेवा प्राधिकरण हेल्पलाइन (NALSA / DLSA):',
    tollFree: '15100 (मोफत, 24x7)',
    police: 'पोलीस: 112',
    cyberCrime: 'सायबर गुन्हे: 1930',
    women: 'महिला हेल्पलाइन: 1091',
    appTitle: 'न्यायवार्ता',
    appSubtitle: 'भारतीय नागरिकांसाठी बहुभाषिक कायदेशीर सहाय्यक (IPC → BNS / CrPC → BNSS / BSA)',
    apiOnline: 'सक्रिय (Online)',
    tabChat: 'कायदेशीर सल्ला (Legal Chat)',
    tabUpload: 'दस्तऐवज / अहवाल जोडा (Upload Document)',
    tabMatrix: 'कायदा बदल तक्ता (Law Matrix)',
    ragTag: 'GraphRAG + Neo4j',
    chatHeader: 'न्यायवार्ता AI कायदेशीर सहाय्यक',
    chatSubtitle: 'भारतीय न्याय संहिता (BNS) आणि मोफत कायदेशीर मदत',
    chatGreeting: 'नमस्कार! न्यायवार्ता आज आपल्याला कशी मदत करू शकते?',
    chatGreetingSub: 'आपल्या भाषेत लिहा, बोला किंवा आपला एफआयआर/दस्तऐवज अपलोड करा. आमचा नॉलेज ग्राफ योग्य कलमे आणि कायदेशीर मार्गदर्शन देईल.',
    suggestedQueriesTitle: 'सुचवलेले कायदेशीर प्रश्न',
    suggestedQueries: [
      {
        label: 'झिरो एफआयआर (BNSS 173)',
        text: 'एफआयआर कशी नोंदवावी? झिरो एफआयआर कायदेशीररित्या वैध आहे का?',
      },
      {
        label: 'फसवणूक (IPC 420 → BNS 318)',
        text: 'जुने IPC 420 आणि नवीन BNS 318 (फसवणूक) यामध्ये काय फरक आहे?',
      },
      {
        label: 'अटकेचे अधिकार (BNSS 35)',
        text: 'BNSS कलम 35 अन्वये अटक करताना नागरिकांचे कोणते अधिकार आहेत?',
      },
      {
        label: 'मोफत कायदेशीर मदत (15100)',
        text: 'ज्येष्ठ नागरिकांसाठी मोफत विधी सेवा आणि NALSA 15100 ची माहिती द्या.',
      },
    ],
    inputPlaceholder: 'आपला कायदेशीर प्रश्न येथे लिहा किंवा बोलण्यासाठी माईक दाबा...',
    sendBtn: 'पाठवा (Send)',
    listening: 'ऐकत आहे...',
    stopSend: 'थांबवा आणि पाठवा',
    attachDoc: 'दस्तऐवज जोडा (PDF / DOCX)',
    docAttached: 'दस्तऐवज जोडला गेला',
    matrixTitle: 'प्रमुख गुन्हेगारी कायदा बदल (IPC → BNS / CrPC → BNSS / IEA → BSA)',
    matrixSubtitle: '1 जुलै 2024 पासून लागू झालेले नवीन कायद्यांचे प्रमुख बदल:',
    matrixHeaders: {
      crime: 'गुन्हा / विषय',
      oldLaw: 'जुने कलम (Old)',
      newLaw: 'नवीन कलम (BNS/BNSS)',
      note: 'महत्त्वाचे बदल',
    },
    historyTitle: 'सल्लामसलत इतिहास (History)',
    newConsultationBtn: '+ नवीन सल्लामसलत (+ New)',
    noHistoryTitle: 'कोणताही जुना सल्ला नाही',
    noHistorySub: 'कायदेशीर प्रश्न विचारून नवीन सल्लामसलत सुरू करा.',
    privateHistoryTitle: 'खाजगी कायदेशीर इतिहास',
    privateHistorySub: 'आपली कायदेशीर चर्चा सुरक्षित ठेवण्यासाठी लॉग इन करा.',
    loginSignUpBtn: 'लॉग इन / साइन अप',
    loadingConsultations: 'लोड होत आहे...',
    messagesCount: 'संदेश',
    privateDataBadge: 'माहिती सुरक्षित',
    hideHistoryBtn: 'इतिहास लपवा',
    showHistoryBtn: 'इतिहास',
    clearChatBtn: 'साफ करा',
    userLoginBtn: 'लॉग इन / खाते',
    userLogOutBtn: 'लॉग आउट',
  },

  // 4. BENGALI (বাংলা)
  bn: {
    emergencyTitle: 'জরুরী ও আইনি সহায়তা',
    legalAidText: 'জাতীয় আইনি পরিষেবা কর্তৃপক্ষ হেল্পলাইন (NALSA / DLSA):',
    tollFree: '15100 (টোল-ফ্রি, 24x7)',
    police: 'পুলিশ: 112',
    cyberCrime: 'সাইবার অপরাধ: 1930',
    women: 'মহিলা হেল্পলাইন: 1091',
    appTitle: 'ন্যায়বার্তা',
    appSubtitle: 'ভারতীয় নাগরিকদের জন্য বহুভাষিক আইনি সহকারী (IPC → BNS / CrPC → BNSS / BSA)',
    apiOnline: 'সক্রিয় (Online)',
    tabChat: 'আইনি পরামর্শ (Legal Chat)',
    tabUpload: 'নথি / রিপোর্ট আপলোড করুন',
    tabMatrix: 'আইন পরিবর্তন তালিকা (Law Matrix)',
    ragTag: 'GraphRAG + Neo4j',
    chatHeader: 'ন্যায়বার্তা AI আইনি সহায়ক',
    chatSubtitle: 'ভারতীয় দণ্ডবিধি (IPC) → ভারতীয় ন্যায় সংহিতা (BNS) ও আইনি সাহায্য',
    chatGreeting: 'নমস্কার! ন্যায়বার্তা আজ আপনাকে কীভাবে সাহায্য করতে পারে?',
    chatGreetingSub: 'আপনার ভাষায় লিখুন, কথা বলুন বা আপনার আইনি নথি আপলোড করুন। আমাদের নলেজ গ্রাফ আপনাকে সঠিক আইন ও অধিকার সম্পর্কে জানাবে।',
    suggestedQueriesTitle: 'প্রস্তাবিত আইনি প্রশ্ন',
    suggestedQueries: [
      {
        label: 'জিরো এফআইআর (BNSS 173)',
        text: 'এফআইআর (FIR) কীভাবে দায়ের করবেন? জিরো এফআইআর কি বৈধ?',
      },
      {
        label: 'প্রতারণা (IPC 420 → BNS 318)',
        text: 'পুরানো IPC 420 এবং নতুন BNS 318 (প্রতারণা) এর মধ্যে পার্থক্য কী?',
      },
      {
        label: 'গ্রেপ্তারির অধিকার (BNSS 35)',
        text: 'BNSS ধারা 35 এর অধীনে গ্রেপ্তারির সময় নাগরিকের অধিকার কী কী?',
      },
      {
        label: 'বিনামূল্যে আইনি সাহায্য (15100)',
        text: 'বিনামূল্যে আইনি সহায়তা পেতে নালসা (NALSA) হেল্পলাইন 15100 কীভাবে কাজ করে?',
      },
    ],
    inputPlaceholder: 'আপনার আইনি প্রশ্ন লিখুন বা কথা বলতে মাইক ক্লিক করুন...',
    sendBtn: 'পাঠান',
    listening: 'শুনছি...',
    stopSend: 'থামুন ও পাঠান',
    attachDoc: 'নথি যুক্ত করুন (PDF / DOCX)',
    docAttached: 'নথি যুক্ত হয়েছে',
    matrixTitle: 'প্রধান ফৌজদারি আইন পরিবর্তন (IPC → BNS / CrPC → BNSS)',
    matrixSubtitle: '১ জুলাই ২০২৪ থেকে কার্যকর নতুন আইনের ধারা পরিবর্তন:',
    matrixHeaders: {
      crime: 'অপরাধ / বিষয়',
      oldLaw: 'পুরানো ধারা (Old)',
      newLaw: 'নতুন ধারা (New)',
      note: 'প্রধান পরিবর্তন',
    },
  },

  // 5. TAMIL (தமிழ்)
  ta: {
    emergencyTitle: 'அவசரம் மற்றும் உதவி',
    legalAidText: 'தேசிய சட்ட சேவைகள் ஆணைய உதவி எண் (NALSA / DLSA):',
    tollFree: '15100 (கட்டணமில்லா, 24x7)',
    police: 'காவல்துறை: 112',
    cyberCrime: 'சைபர் குற்றம்: 1930',
    women: 'பெண்கள் உதவி எண்: 1091',
    appTitle: 'நியாயவார்தா',
    appSubtitle: 'இந்தியக் குடிமக்களுக்கான பன்மொழி சட்ட உதவியாளர் (IPC → BNS / CrPC → BNSS / BSA)',
    apiOnline: 'செயலில் உள்ளது',
    tabChat: 'சட்ட ஆலோசனை (Legal Chat)',
    tabUpload: 'ஆவணத்தைப் பதிவேற்றுக',
    tabMatrix: 'சட்ட மாற்ற அட்டவணை',
    ragTag: 'GraphRAG + Neo4j',
    chatHeader: 'நியாயவார்தா AI சட்ட உதவியாளர்',
    chatSubtitle: 'இந்திய தண்டனைச் சட்டம் (IPC) → பாரதிய நியாய சன்ஹிதா (BNS)',
    chatGreeting: 'வணக்கம்! நியாயவார்தா உங்களுக்கு இன்று எவ்வாறு உதவ முடியும்?',
    chatGreetingSub: 'உங்கள் மொழியில் தட்டச்சு செய்யவும், பேசவும் அல்லது உங்கள் புகாரை பதிவேற்றவும்.',
    suggestedQueriesTitle: 'பரிந்துரைக்கப்பட்ட சட்டக் கேள்விகள்',
    suggestedQueries: [
      {
        label: 'ஜீரோ எஃப்.ஐ.ஆர் (BNSS 173)',
        text: 'எஃப்ஐஆர் பதிவு செய்வது எப்படி? ஜீரோ எஃப்ஐஆர் செல்லுபடியாகுமா?',
      },
      {
        label: 'மோசடி (IPC 420 → BNS 318)',
        text: 'பழைய IPC 420 மற்றும் புதிய BNS 318 இடையே உள்ள வேறுபாடு என்ன?',
      },
      {
        label: 'கைது உரிமைகள் (BNSS 35)',
        text: 'BNSS பிரிவு 35 இன் கீழ் கைது செய்யப்படும் போது குடிமக்களின் உரிமைகள் யாவை?',
      },
      {
        label: 'இலவச சட்ட உதவி (15100)',
        text: 'நல்சா (NALSA) 15100 உதவி எண் மூலம் இலவச சட்ட உதவி பெறுவது எப்படி?',
      },
    ],
    inputPlaceholder: 'உங்கள் சட்டக் கேள்வியை உள்ளிடவும் அல்லது மைக் கிளிக் செய்யவும்...',
    sendBtn: 'அனுப்புக',
    listening: 'கேட்கிறது...',
    stopSend: 'நிறுத்தி அனுப்புக',
    attachDoc: 'ஆவணத்தை இணைக்கவும் (PDF / DOCX)',
    docAttached: 'ஆவணம் இணைக்கப்பட்டது',
    matrixTitle: 'முக்கிய குற்றவியல் சட்ட மாற்றங்கள் (IPC → BNS)',
    matrixSubtitle: 'ஜூலை 1, 2024 முதல் நடைமுறைக்கு வந்துள்ள புதிய சட்டப் பிரிவுகள்:',
    matrixHeaders: {
      crime: 'குற்றம் / பொருள்',
      oldLaw: 'பழைய பிரிவு',
      newLaw: 'புதிய பிரிவு (2023)',
      note: 'முக்கிய குறிப்பு',
    },
  },

  // 6. TELUGU (తెలుగు)
  te: {
    emergencyTitle: 'అత్యవసర మరియు చట్టపరమైన సహాయం',
    legalAidText: 'జాతీయ న్యాయ సేవల ప్రాధికార సంస్థ హెల్ప్‌లైన్ (NALSA / DLSA):',
    tollFree: '15100 (ఉచితం, 24x7)',
    police: 'పోలీస్: 112',
    cyberCrime: 'సైబర్ నేరాలు: 1930',
    women: 'మహిళల హెల్ప్‌లైన్: 1091',
    appTitle: 'న్యాయవార్త',
    appSubtitle: 'భారతీయ పౌరుల కోసం బహుభాషా చట్టపరమైన సహాయకుడు (IPC → BNS)',
    apiOnline: 'యాక్టివ్ (Online)',
    tabChat: 'చట్టపరమైన సలహా (Legal Chat)',
    tabUpload: 'పత్రం / నివేదికను అప్‌లోడ్ చేయండి',
    tabMatrix: 'చట్టాల మార్పు పట్టిక',
    ragTag: 'GraphRAG + Neo4j',
    chatHeader: 'న్యాయవార్త AI న్యాయ సహాయకుడు',
    chatSubtitle: 'భారతీయ శిక్షాస్మృతి (IPC) → భారతీయ న్యాయ సంహిత (BNS)',
    chatGreeting: 'నమస్కారం! న్యాయవార్త మీకు ఈరోజు ఎలా సహాయం చేయగలదు?',
    chatGreetingSub: 'మీ భాషలో రాయండి, మాట్లాడండి లేదా మీ ఎఫ్ఐఆర్ పత్రాన్ని అప్‌లోడ్ చేయండి.',
    suggestedQueriesTitle: 'సూచించిన చట్టపరమైన ప్రశ్నలు',
    suggestedQueries: [
      {
        label: 'జీరో ఎఫ్ఐఆర్ (BNSS 173)',
        text: 'ఎఫ్ఐఆర్ ఎలా నమోదు చేయాలి? జీరో ఎఫ్ఐఆర్ చెల్లుతుందా?',
      },
      {
        label: 'మోసం (IPC 420 → BNS 318)',
        text: 'పాత IPC 420 మరియు కొత్త BNS 318 మధ్య తేడా ఏమిటి?',
      },
      {
        label: 'అరెస్ట్ హక్కులు (BNSS 35)',
        text: 'BNSS సెక్షన్ 35 ప్రకారం అరెస్ట్ సమయంలో పౌరుల హక్కులు ఏమిటి?',
      },
      {
        label: 'ఉచిత న్యాయ సహాయం (15100)',
        text: 'ఉచిత న్యాయ సహాయం కోసం NALSA 15100 ఎలా సంప్రదించాలి?',
      },
    ],
    inputPlaceholder: 'మీ ప్రశ్నను ఇక్కడ నమోదు చేయండి లేదా మాట్లాడటానికి మైక్ నొక్కండి...',
    sendBtn: 'పంపండి',
    listening: 'వింటోంది...',
    stopSend: 'ఆపి పంపండి',
    attachDoc: 'పత్రం జతచేయండి (PDF / DOCX)',
    docAttached: 'పత్రం జోడించబడింది',
    matrixTitle: 'ప్రధాన నేర చట్టాల మార్పులు (IPC → BNS / CrPC → BNSS)',
    matrixSubtitle: 'జులై 1, 2024 నుండి అమల్లోకి వచ్చిన కొత్త చట్టాల సెక్షన్లు:',
    matrixHeaders: {
      crime: 'నేరం / అంశం',
      oldLaw: 'పాత సెక్షన్',
      newLaw: 'కొత్త సెక్షన్',
      note: 'ముఖ్య మార్పులు',
    },
  },

  // 7. GUJARATI (ગુજરાતી)
  gu: {
    emergencyTitle: 'કટોકટી અને કાનૂની સહાય',
    legalAidText: 'રાષ્ટ્રીય કાનૂની સેવા સત્તામંડળ હેલ્પલાઇન (NALSA / DLSA):',
    tollFree: '15100 (ટોલ-ફ્રી, 24x7)',
    police: 'પોલીસ: 112',
    cyberCrime: 'સાયબર ક્રાઇમ: 1930',
    women: 'મહિલા હેલ્પલાઇન: 1091',
    appTitle: 'ન્યાયવાર્તા',
    appSubtitle: 'ભારતીય નાગરિકો માટે બહુભાષી કાનૂની સહાયક (IPC → BNS / BNSS / BSA)',
    apiOnline: 'સક્રિય (Online)',
    tabChat: 'કાનૂની સલાહ (Legal Chat)',
    tabUpload: 'દસ્તાવેજ અપલોડ કરો',
    tabMatrix: 'કાયદા પરિવર્તન ચાર્ટ',
    ragTag: 'GraphRAG + Neo4j',
    chatHeader: 'ન્યાયવાર્તા AI કાનૂની સહાયક',
    chatSubtitle: 'ભારતીય દંડ સંહિતા (IPC) → ભારતીય ન્યાય સંહિતા (BNS)',
    chatGreeting: 'નમસ્તે! ન્યાયવાર્તા આજે આપને કેવી રીતે મદદ કરી શકે છે?',
    chatGreetingSub: 'તમારી ભાષામાં લખો, બોલો અથવા કાનૂની અહેવાલ અપલોડ કરો.',
    suggestedQueriesTitle: 'સૂચવેલા કાનૂની પ્રશ્નો',
    suggestedQueries: [
      {
        label: 'ઝીરો એફઆઇઆર (BNSS 173)',
        text: 'FIR કેવી રીતે નોંધાવવી? શું ઝીરો એફઆઈઆર માન્ય છે?',
      },
      {
        label: 'છેતરપિંડી (IPC 420 → BNS 318)',
        text: 'જૂની IPC 420 અને નવી BNS 318 (છેતરપિંડી) વચ્ચે શું તફાવત છે?',
      },
      {
        label: 'ધરપકડ અધિકારો (BNSS 35)',
        text: 'BNSS કલમ 35 હેઠળ ધરપકડ સમયે નાગરિકોના કયા અધિકારો છે?',
      },
      {
        label: 'મફત કાનૂની સહાય (15100)',
        text: 'નાગરિકો NALSA 15100 પરથી મફત કાનૂની સહાય કેવી રીતે મેળવી શકે?',
      },
    ],
    inputPlaceholder: 'તમારો પ્રશ્ન અહીં લખો અથવા બોલવા માટે માઇક ક્લિક કરો...',
    sendBtn: 'મોકલો',
    listening: 'સાંભળી રહ્યું છે...',
    stopSend: 'રોકો અને મોકલો',
    attachDoc: 'દસ્તાવેજ જોડો (PDF / DOCX)',
    docAttached: 'દસ્તાવેજ જોડાઈ ગયો',
    matrixTitle: 'મુખ્ય ફોજદારી કાયદા પરિવર્તન (IPC → BNS)',
    matrixSubtitle: '1 જુલાઈ 2024 થી અમલમાં આવેલા નવા કાયદાની કલમો:',
    matrixHeaders: {
      crime: 'ગુનો / વિષય',
      oldLaw: 'જૂની કલમ',
      newLaw: 'નવી કલમ',
      note: 'મહત્વના ફેરફાર',
    },
  },

  // 8. KANNADA (ಕನ್ನಡ)
  kn: {
    emergencyTitle: 'ತುರ್ತು ಮತ್ತು ಕಾನೂನು ನೆರವು',
    legalAidText: 'ರಾಷ್ಟ್ರೀಯ ಕಾನೂನು ಸೇವೆಗಳ ಪ್ರಾಧಿಕಾರ ಸಹಾಯವಾಣಿ (NALSA / DLSA):',
    tollFree: '15100 (ಉಚಿತ, 24x7)',
    police: 'ಪೊಲೀಸ್: 112',
    cyberCrime: 'ಸೈಬರ್ ಅಪರಾಧ: 1930',
    women: 'ಮಹಿಳಾ ಸಹಾಯವಾಣಿ: 1091',
    appTitle: 'ನ್ಯಾಯವಾರ್ತಾ',
    appSubtitle: 'ಭಾರತೀಯ ನಾಗರಿಕರಿಗೆ ಬಹುಭಾಷಾ ಕಾನೂನು ಸಹಾಯಕ (IPC → BNS / BNSS)',
    apiOnline: 'ಸಕ್ರಿಯವಾಗಿದೆ',
    tabChat: 'ಕಾನೂನು ಸಮಾಲೋಚನೆ',
    tabUpload: 'ದಾಖಲೆ / ವರದಿ ಅಪ್‌ಲೋಡ್ ಮಾಡಿ',
    tabMatrix: 'ಕಾನೂನು ಬದಲಾವಣೆ ಪಟ್ಟಿ',
    ragTag: 'GraphRAG + Neo4j',
    chatHeader: 'ನ್ಯಾಯವಾರ್ತಾ AI ಕಾನೂನು ಸಹಾಯಕ',
    chatSubtitle: 'ಭಾರತೀಯ ದಂಡ ಸಂಹಿತೆ (IPC) → ಭಾರತೀಯ ನ್ಯಾಯ ಸಂಹಿತಾ (BNS)',
    chatGreeting: 'ನಮಸ್ಕಾರ! ನ್ಯಾಯವಾರ್ತಾ ನಿಮಗೆ ಇಂದು ಹೇಗೆ ಸಹಾಯ ಮಾಡಬಹುದು?',
    chatGreetingSub: 'ನಿಮ್ಮ ಭಾಷೆಯಲ್ಲಿ ಬರೆಯಿರಿ, ಮಾತನಾಡಿ ಅಥವಾ ನಿಮ್ಮ ಎಫ್‌ಐಆರ್ ದಾಖಲೆಯನ್ನು ಅಪ್‌ಲೋಡ್ ಮಾಡಿ.',
    suggestedQueriesTitle: 'ಸೂಚಿಸಲಾದ ಕಾನೂನು ಪ್ರಶ್ನೆಗಳು',
    suggestedQueries: [
      {
        label: 'ಜೀರೋ ಎಫ್‌ಐಆರ್ (BNSS 173)',
        text: 'ಎಫ್‌ಐಆರ್ ದಾಖಲಿಸುವುದು ಹೇಗೆ? ಜೀರೋ ಎಫ್‌ಐಆರ್ ಮಾನ್ಯವಾಗಿದೆಯೇ?',
      },
      {
        label: 'ವಂಚನೆ (IPC 420 → BNS 318)',
        text: 'ಹಳೆಯ IPC 420 ಮತ್ತು ಹೊಸ BNS 318 ನಡುವಿನ ವ್ಯತ್ಯಾಸವೇನು?',
      },
      {
        label: 'ಬಂಧನದ ಹಕ್ಕುಗಳು (BNSS 35)',
        text: 'BNSS ಸೆಕ್ಷನ್ 35 ರ ಅಡಿಯಲ್ಲಿ ಬಂಧನದ ಸಮಯದಲ್ಲಿ ನಾಗರಿಕರ ಹಕ್ಕುಗಳೇನು?',
      },
      {
        label: 'ಉಚಿತ ಕಾನೂನು ನೆರವು (15100)',
        text: 'NALSA 15100 ಸಹಾಯವಾಣಿಯಿಂದ ಉಚಿತ ಕಾನೂನು ನೆರವು ಪಡೆಯುವುದು ಹೇಗೆ?',
      },
    ],
    inputPlaceholder: 'ನಿಮ್ಮ ಕಾನೂನು ಪ್ರಶ್ನೆಯನ್ನು ನಮೂದಿಸಿ ಅಥವಾ ಮಾತನಾಡಲು ಮೈಕ್ ಕ್ಲಿಕ್ ಮಾಡಿ...',
    sendBtn: 'ಕಳುಹಿಸಿ',
    listening: 'ಆಲಿಸುತ್ತಿದೆ...',
    stopSend: 'ನಿಲ್ಲಿಸಿ ಕಳುಹಿಸಿ',
    attachDoc: 'ದಾಖಲೆ ಲಗತ್ತಿಸಿ (PDF / DOCX)',
    docAttached: 'ದಾಖಲೆ ಲಗತ್ತಿಸಲಾಗಿದೆ',
    matrixTitle: 'ಪ್ರಮುಖ ಕ್ರಿಮಿನಲ್ ಕಾನೂನು ಬದಲಾವಣೆಗಳು (IPC → BNS)',
    matrixSubtitle: 'ಜುಲೈ 1, 2024 ರಿಂದ ಜಾರಿಗೆ ಬಂದ ಹೊಸ ಕಾನೂನಿನ ಸೆಕ್ಷನ್‌ಗಳು:',
    matrixHeaders: {
      crime: 'ಅಪರಾಧ / ವಿಷಯ',
      oldLaw: 'ಹಳೆಯ ಸೆಕ್ಷನ್',
      newLaw: 'ಹೊಸ ಸೆಕ್ಷನ್',
      note: 'ಪ್ರಮುಖ ಟಿಪ್ಪಣಿ',
    },
  },

  // 9. MALAYALAM (മലയാളം)
  ml: {
    emergencyTitle: 'അടിയന്തര നിയമ സഹായം',
    legalAidText: 'ദേശീയ നിയമ സേവന അതോറിറ്റി ഹെൽപ്പ് ലൈൻ (NALSA / DLSA):',
    tollFree: '15100 (ടോൾ ഫ്രീ, 24x7)',
    police: 'പോലീസ്: 112',
    cyberCrime: 'സൈബർ കുറ്റകൃത്യങ്ങൾ: 1930',
    women: 'വനിതാ ഹെൽപ്പ് ലൈൻ: 1091',
    appTitle: 'ന്യായവാർത്ത',
    appSubtitle: 'ഇന്ത്യൻ പൗരന്മാർക്കുള്ള ബഹുഭാഷാ നിയമ സഹായി (IPC → BNS / BNSS)',
    apiOnline: 'സജീവം (Online)',
    tabChat: 'നിയമ സംഭാഷണം',
    tabUpload: 'രേഖകൾ അപ്‌ലോഡ് ചെയ്യുക',
    tabMatrix: 'നിയമ മാറ്റ പട്ടിക',
    ragTag: 'GraphRAG + Neo4j',
    chatHeader: 'ന്യായവാർത്ത AI നിയമ സഹായി',
    chatSubtitle: 'ഇന്ത്യൻ പീനൽ കോഡ് (IPC) → ഭാരതീയ ന്യായ സംഹിത (BNS)',
    chatGreeting: 'നമസ്കാരം! ന്യായവാർത്തയ്ക്ക് ഇന്ന് നിങ്ങളെ എങ്ങനെ സഹായിക്കാനാകും?',
    chatGreetingSub: 'നിങ്ങളുടെ ഭാഷയിൽ ടൈപ്പ് ചെയ്യുകയോ സംസാരിക്കുകയോ രേഖകൾ അപ്‌ലോഡ് ചെയ്യുകയോ ചെയ്യാം.',
    suggestedQueriesTitle: 'നിർദ്ദേശിച്ച നിയമ ചോദ്യങ്ങൾ',
    suggestedQueries: [
      {
        label: 'സീറോ എഫ്ഐആർ (BNSS 173)',
        text: 'എഫ്ഐആർ എങ്ങനെ ഫയൽ ചെയ്യാം? സീറോ എഫ്ഐആർ സാധുവാണോ?',
      },
      {
        label: 'തട്ടിപ്പ് (IPC 420 → BNS 318)',
        text: 'പഴയ IPC 420 ഉം പുതിയ BNS 318 ഉം തമ്മിലുള്ള വ്യത്യാസം എന്താണ്?',
      },
      {
        label: 'അറസ്റ്റ് അവകാശങ്ങൾ (BNSS 35)',
        text: 'BNSS സെക്ഷൻ 35 പ്രകാരം അറസ്റ്റിലാകുമ്പോൾ പൗരന്റെ അവകാശങ്ങൾ എന്തൊക്കെയാണ്?',
      },
      {
        label: 'സൗജന്യ നിയമ സഹായം (15100)',
        text: 'നൽസ 15100 വഴി സൗജന്യ നിയമ സഹായം എങ്ങനെ നേടാം?',
      },
    ],
    inputPlaceholder: 'നിങ്ങളുടെ ചോദ്യം ടൈപ്പ് ചെയ്യുക അല്ലെങ്കിൽ സംസാരിക്കാൻ മൈക്ക് ക്ലിക്ക് ചെയ്യുക...',
    sendBtn: 'അയക്കുക',
    listening: 'കേൾക്കുന്നു...',
    stopSend: 'നിർത്തുക & അയക്കുക',
    attachDoc: 'രേഖ ചേർക്കുക (PDF / DOCX)',
    docAttached: 'രേഖ ചേർത്തു',
    matrixTitle: 'പ്രധാന ക്രിമിനൽ നിയമ മാറ്റങ്ങൾ (IPC → BNS)',
    matrixSubtitle: '2024 ജൂലൈ 1 മുതൽ പ്രാബല്യത്തിൽ വന്ന പുതിയ നിയമങ്ങൾ:',
    matrixHeaders: {
      crime: 'കുറ്റകൃത്യം / വിഷയം',
      oldLaw: 'പഴയ വകുപ്പ്',
      newLaw: 'പുതിയ വകുപ്പ്',
      note: 'പ്രധാന മാറ്റങ്ങൾ',
    },
  },

  // 10. PUNJABI (ਪੰਜਾਬੀ)
  pa: {
    emergencyTitle: 'ਐਮਰਜੈਂਸੀ ਅਤੇ ਕਾਨੂੰਨੀ ਸਹਾਇਤਾ',
    legalAidText: 'ਰਾਸ਼ਟਰੀ ਕਾਨੂੰਨੀ ਸੇਵਾਵਾਂ ਅਥਾਰਟੀ ਹੈਲਪਲਾਈਨ (NALSA / DLSA):',
    tollFree: '15100 (ਟੋਲ-ਫ੍ਰੀ, 24x7)',
    police: 'ਪੁਲਿਸ: 112',
    cyberCrime: 'ਸਾਈਬਰ ਅਪਰਾਧ: 1930',
    women: 'ਮਹਿਲਾ ਹੈਲਪਲਾਈਨ: 1091',
    appTitle: 'ਨਿਆਇਵਾਰਤਾ',
    appSubtitle: 'ਭਾਰਤੀ ਨਾਗਰਿਕਾਂ ਲਈ ਬਹੁਭਾਸ਼ਾਈ ਕਾਨੂੰਨੀ ਸਹਾਇਕ (IPC → BNS / BNSS)',
    apiOnline: 'ਸਰਗਰਮ (Online)',
    tabChat: 'ਕਾਨੂੰਨੀ ਸਲਾਹ (Legal Chat)',
    tabUpload: 'ਦਸਤਾਵੇਜ਼ ਅਪਲੋਡ ਕਰੋ',
    tabMatrix: 'ਕਾਨੂੰਨ ਬਦਲਾਅ ਚਾਰਟ',
    ragTag: 'GraphRAG + Neo4j',
    chatHeader: 'ਨਿਆਇਵਾਰਤਾ AI ਕਾਨੂੰਨੀ ਸਹਾਇਕ',
    chatSubtitle: 'ਭਾਰਤੀ ਦੰਡਾਵਲੀ (IPC) → ਭਾਰਤੀ ਨਿਆਂ ਸੰਹਿਤਾ (BNS)',
    chatGreeting: 'ਸਤਿ ਸ੍ਰੀ ਅਕਾਲ! ਨਿਆਇਵਾਰਤਾ ਅੱਜ ਤੁਹਾਡੀ ਕੀ ਮਦਦ ਕਰ ਸਕਦੀ ਹੈ?',
    chatGreetingSub: 'ਆਪਣੀ ਭਾਸ਼ਾ ਵਿੱਚ ਲਿਖੋ, ਬੋਲੋ ਜਾਂ ਦਸਤਾਵੇਜ਼ ਅਪਲੋਡ ਕਰੋ।',
    suggestedQueriesTitle: 'ਸੁਝਾਏ ਗਏ ਕਾਨੂੰਨੀ ਸਵਾਲ',
    suggestedQueries: [
      {
        label: 'ਜ਼ੀਰੋ ਐਫਆਈਆਰ (BNSS 173)',
        text: 'ਐਫਆਈਆਰ ਕਿਵੇਂ ਦਰਜ ਕਰਵਾਈ ਜਾਵੇ? ਕੀ ਜ਼ੀਰੋ ਐਫਆਈਆਰ ਜਾਇਜ਼ ਹੈ?',
      },
      {
        label: 'ਧੋਖਾਧੜੀ (IPC 420 → BNS 318)',
        text: 'ਪੁਰਾਣੀ IPC 420 ਅਤੇ ਨਵੀਂ BNS 318 ਵਿੱਚ ਕੀ ਫਰਕ ਹੈ?',
      },
      {
        label: 'ਗ੍ਰਿਫਤਾਰੀ ਅਧਿਕਾਰ (BNSS 35)',
        text: 'BNSS ਧਾਰਾ 35 ਅਧੀਨ ਗ੍ਰਿਫਤਾਰੀ ਸਮੇਂ ਨਾਗਰਿਕ ਦੇ ਕੀ ਅਧਿਕਾਰ ਹਨ?',
      },
      {
        label: 'ਮੁਫਤ ਕਾਨੂੰਨੀ ਸਹਾਇਤਾ (15100)',
        text: 'ਨਾਲਸਾ 15100 ਤੋਂ ਮੁਫਤ ਕਾਨੂੰਨੀ ਸਹਾਇਤਾ ਕਿਵੇਂ ਲਈਏ?',
      },
    ],
    inputPlaceholder: 'ਆਪਣਾ ਕਾਨੂੰਨੀ ਸਵਾਲ ਇੱਥੇ ਲਿਖੋ ਜਾਂ ਬੋਲਣ ਲਈ ਮਾਈਕ ਦਬਾਓ...',
    sendBtn: 'ਭੇਜੋ',
    listening: 'ਸੁਣ ਰਿਹਾ ਹੈ...',
    stopSend: 'ਰੋਕੋ ਅਤੇ ਭੇਜੋ',
    attachDoc: 'ਦਸਤਾਵੇਜ਼ ਜੋੜੋ (PDF / DOCX)',
    docAttached: 'ਦਸਤਾਵੇਜ਼ ਜੋੜਿਆ ਗਿਆ',
    matrixTitle: 'ਮੁੱਖ ਅਪਰਾਧਿਕ ਕਾਨੂੰਨ ਬਦਲਾਅ (IPC → BNS)',
    matrixSubtitle: '1 ਜੁਲਾਈ 2024 ਤੋਂ ਲਾਗੂ ਹੋਏ ਨਵੇਂ ਕਾਨੂੰਨ:',
    matrixHeaders: {
      crime: 'ਅਪਰਾਧ / ਵਿਸ਼ਾ',
      oldLaw: 'ਪੁਰਾਣੀ ਧਾਰਾ',
      newLaw: 'ਨਵੀਂ ਧਾਰਾ',
      note: 'ਮੁੱਖ ਨੁਕਤੇ',
    },
  },

  // 11. ODIA (ଓଡ଼ିଆ)
  or: {
    emergencyTitle: 'ଜରୁରୀକାଳୀନ ଏବଂ ଆଇନଗତ ସହାୟତା',
    legalAidText: 'ଜାତୀୟ ଆଇନ ସେବା ପ୍ରାଧିକରଣ ହେଲ୍ପଲାଇନ (NALSA / DLSA):',
    tollFree: '15100 (ଟୋଲ-ଫ୍ରି, 24x7)',
    police: 'ପୋଲିସ: 112',
    cyberCrime: 'ସାଇବର ଅପରାଧ: 1930',
    women: 'ମହିଳା ହେଲ୍ପଲାଇନ: 1091',
    appTitle: 'ନ୍ୟାୟବାର୍ତ୍ତା',
    appSubtitle: 'ଭାରତୀୟ ନାଗରିକଙ୍କ ପାଇଁ ବହୁଭାଷୀ ଆଇନ ସହାୟକ (IPC → BNS)',
    apiOnline: 'ସକ୍ରିୟ (Online)',
    tabChat: 'ଆଇନ ପରାମର୍ଶ (Legal Chat)',
    tabUpload: 'ଦଲିଲ ଅପଲୋଡ୍ କରନ୍ତୁ',
    tabMatrix: 'ଆଇନ ପରିବର୍ତ୍ତନ ଚାର୍ଟ',
    ragTag: 'GraphRAG + Neo4j',
    chatHeader: 'ନ୍ୟାୟବାର୍ତ୍ତା AI ଆଇନ ସହାୟକ',
    chatSubtitle: 'ଭାରତୀୟ ଦଣ୍ଡବିଧି (IPC) → ଭାରତୀୟ ନ୍ୟାୟ ସଂହିତା (BNS)',
    chatGreeting: 'ନମସ୍କାର! ନ୍ୟାୟବାର୍ତ୍ତା ଆଜି ଆପଣଙ୍କୁ କିପରି ସାହାଯ୍ୟ କରିପାରିବ?',
    chatGreetingSub: 'ନିଜ ଭାଷାରେ ଲେଖନ୍ତୁ, କୁହନ୍ତୁ କିମ୍ବା ଆପଣଙ୍କ ରିପୋର୍ଟ ଅପଲୋଡ୍ କରନ୍ତୁ।',
    suggestedQueriesTitle: 'ପ୍ରସ୍ତାବିତ ଆଇନଗତ ପ୍ରଶ୍ନ',
    suggestedQueries: [
      {
        label: 'ଜିରୋ ଏଫଆଇଆର (BNSS 173)',
        text: 'FIR କିପରି ରୁଜୁ କରିବେ? ଜିରୋ FIR ବୈଧ କି?',
      },
      {
        label: 'ଠକେଇ (IPC 420 → BNS 318)',
        text: 'ପୁରୁଣା IPC 420 ଏବଂ ନୂଆ BNS 318 ମଧ୍ୟରେ କଣ ପାର୍ଥକ୍ୟ ଅଛି?',
      },
      {
        label: 'ଗିରଫ ଅଧିକାର (BNSS 35)',
        text: 'BNSS ଧାରା 35 ଅନୁଯାୟୀ ଗିରଫ ସମୟରେ ନାଗରିକଙ୍କ ଅଧିକାର କଣ?',
      },
      {
        label: 'ମାଗଣା ଆଇନ ସହାୟତା (15100)',
        text: 'ନାଲସା 15100 ରୁ ମାଗଣା ଆଇନ ସହାୟତା କିପରି ପାଇବେ?',
      },
    ],
    inputPlaceholder: 'ଆପଣଙ୍କ ପ୍ରଶ୍ନ ଲେଖନ୍ତୁ କିମ୍ବା କହିବାକୁ ମାଇକ୍ କ୍ଲିକ୍ କରନ୍ତୁ...',
    sendBtn: 'ପଠାନ୍ତୁ',
    listening: 'ଶୁଣୁଛି...',
    stopSend: 'ବନ୍ଦ କରି ପଠାନ୍ତୁ',
    attachDoc: 'ଦଲିଲ ଯୋଡନ୍ତୁ (PDF / DOCX)',
    docAttached: 'ଦଲିଲ ଯୋଡାଗଲା',
    matrixTitle: 'ମୁଖ୍ୟ ଫୌଜଦାରୀ ଆଇନ ପରିବର୍ତ୍ତନ (IPC → BNS)',
    matrixSubtitle: '୧ ଜୁଲାଇ ୨୦୨୪ ରୁ ଲାଗୁ ନୂତନ ଆଇନ ଧାରା:',
    matrixHeaders: {
      crime: 'ଅପରାଧ / ବିଷୟ',
      oldLaw: 'ପୁରୁଣା ଧାରା',
      newLaw: 'ନୂତନ ଧାରା',
      note: 'ମୁଖ୍ୟ ଟିପ୍ପଣୀ',
    },
  },

  // 12. URDU (اردو)
  ur: {
    emergencyTitle: 'ہنگامی اور قانونی امداد',
    legalAidText: 'قومی قانونی خدمات اتھارٹی ہیلپ لائن (NALSA / DLSA):',
    tollFree: '15100 (ٹول فری، 24x7)',
    police: 'پولیس: 112',
    cyberCrime: 'سائبر کرائم: 1930',
    women: 'خواتین ہیلپ لائن: 1091',
    appTitle: 'نیاۓ وارتا',
    appSubtitle: 'ہندوستانی شہریوں کے لیے کثیر لسانی قانونی معاون (IPC → BNS)',
    apiOnline: 'فعال (Online)',
    tabChat: 'قانونی مشورہ (Legal Chat)',
    tabUpload: 'دستاویز / رپورٹ اپ لوڈ کریں',
    tabMatrix: 'قانون منتقلی چارٹ',
    ragTag: 'GraphRAG + Neo4j',
    chatHeader: 'نیاۓ وارتا AI قانونی معاون',
    chatSubtitle: 'تعزیرات ہند (IPC) → بھارتیہ نیائے سنہیتا (BNS)',
    chatGreeting: 'آداب! نیاۓ وارتا آج آپ کی کس طرح مدد کر سکتا ہے؟',
    chatGreetingSub: 'اپنی زبان میں لکھیں، بولیں یا اپنی رپورٹ اپ لوڈ کریں۔',
    suggestedQueriesTitle: 'تجویز کردہ قانونی سوالات',
    suggestedQueries: [
      {
        label: 'زیرو ایف آئی آر (BNSS 173)',
        text: 'ایف آئی آر کیسے درج کروائیں؟ کیا زیرو ایف آئی آر قانونی طور پر درست ہے؟',
      },
      {
        label: 'دھوکہ دہی (IPC 420 → BNS 318)',
        text: 'پرانی IPC 420 اور نئی BNS 318 میں کیا فرق ہے؟',
      },
      {
        label: 'گرفتاری کے حقوق (BNSS 35)',
        text: 'BNSS دفعہ 35 کے تحت گرفتاری کے وقت شہری کے کیا حقوق ہیں؟',
      },
      {
        label: 'مفت قانونی امداد (15100)',
        text: 'نالسا 15100 کے ذریعے مفت قانونی امداد کیسے حاصل کی جائے؟',
      },
    ],
    inputPlaceholder: 'اپنا قانونی سوال درج کریں یا بولنے کے لیے مائیک دبائیں...',
    sendBtn: 'ارسال کریں',
    listening: 'آواز سنی جا رہی ہے...',
    stopSend: 'روکیں اور بھیجیں',
    attachDoc: 'دستاویز منسلک کریں (PDF / DOCX)',
    docAttached: 'دستاویز منسلک ہو گئی',
    matrixTitle: 'اہم فوجداری قوانین کی تبدیلیاں (IPC → BNS)',
    matrixSubtitle: '1 جولائی 2024 سے نافذ العمل نئے قوانین:',
    matrixHeaders: {
      crime: 'جرم / موضوع',
      oldLaw: 'پرانی دفعہ',
      newLaw: 'نئی دفعہ',
      note: 'اہم نکات',
    },
  },

  // 13. ASSAMESE (অসমীয়া)
  as: {
    emergencyTitle: 'জৰুৰী আৰু আইনী সাহায্য',
    legalAidText: 'ৰাষ্ট্ৰীয় আইনী সেৱা প্ৰাধিকৰণ হেল্পলাইন (NALSA / DLSA):',
    tollFree: '15100 (টোল-ফ্ৰী, 24x7)',
    police: 'আৰক্ষী: 112',
    cyberCrime: 'চাইবাৰ অপৰাধ: 1930',
    women: 'মহিলা হেল্পলাইন: 1091',
    appTitle: 'ন্যায়বাৰ্তা',
    appSubtitle: 'ভাৰতীয় নাগৰিকৰ বাবে বহুভাষিক আইনী সহায়ক (IPC → BNS)',
    apiOnline: 'সক্ৰিয় (Online)',
    tabChat: 'আইনী পৰামৰ্শ (Legal Chat)',
    tabUpload: 'নথি / ৰিপৰ্ট আপলোড কৰক',
    tabMatrix: 'আইন পৰিৱৰ্তন তালিকা',
    ragTag: 'GraphRAG + Neo4j',
    chatHeader: 'ন্যায়বাৰ্তা AI আইনী সহায়ক',
    chatSubtitle: 'ভাৰতীয় দণ্ডবিধি (IPC) → ভাৰতীয় ন্যায় সংহিতা (BNS)',
    chatGreeting: 'নমস্কাৰ! ন্যায়বাৰ্তাই আজি আপোনাক কেনেকৈ সহায় কৰিব পাৰে?',
    chatGreetingSub: 'আপোনাৰ ভাষাত লিখক, কওক বা আপোনাৰ আইনী নথি আপলোড কৰক।',
    suggestedQueriesTitle: 'প্ৰস্তাৱিত আইনী প্ৰশ্নসমূহ',
    suggestedQueries: [
      {
        label: 'জিৰো এফআইআৰ (BNSS 173)',
        text: 'এফআইআৰ কেনেকৈ দাখিল কৰিব? জিৰো এফআইআৰ বৈধনে?',
      },
      {
        label: 'প্ৰতাৰণা (IPC 420 → BNS 318)',
        text: 'পুৰণি IPC 420 আৰু নতুন BNS 318 ৰ মাজত পাৰ্থক্য কি?',
      },
      {
        label: 'গ্ৰেপ্তাৰৰ অধিকাৰ (BNSS 35)',
        text: 'BNSS ধাৰা 35 ৰ অধীনত গ্ৰেপ্তাৰৰ সময়ত নাগৰিকৰ অধিকাৰ কি কি?',
      },
      {
        label: 'বিনামূলীয়া আইনী সাহায্য (15100)',
        text: 'নালসা 15100 ৰ পৰা বিনামূলীয়া আইনী সাহায্য কেনেকৈ লাভ কৰিব?',
      },
    ],
    inputPlaceholder: 'আপোনাৰ আইনী প্ৰশ্ন লিখক বা ক’বলৈ মাইক ক্লিক কৰক...',
    sendBtn: 'প্ৰেৰণ কৰক',
    listening: 'শুনি থকা হৈছে...',
    stopSend: 'বন্ধ কৰি প্ৰেৰণ কৰক',
    attachDoc: 'নথি সংযোগ কৰক (PDF / DOCX)',
    docAttached: 'নথি সংযুক্ত হ’ল',
    matrixTitle: 'প্ৰধান ফৌজদাৰী আইন পৰিৱৰ্তন (IPC → BNS)',
    matrixSubtitle: '১ জুলাই ২০২৪ ৰ পৰা কাৰ্যকৰী নতুন আইনৰ ধাৰাসমূহ:',
    matrixHeaders: {
      crime: 'অপৰাধ / বিষয়',
      oldLaw: 'পুৰণি ধাৰা',
      newLaw: 'নতুন ধাৰা',
      note: 'মুখ্য পৰিৱৰ্তন',
    },
  },

  // 14. SANSKRIT (संस्कृतम्)
  sa: {
    emergencyTitle: 'आत्ययिकं विधिकसाहाय्यं च',
    legalAidText: 'राष्ट्रीय विधिक सेवा प्राधिकरण हेल्पलाइन (NALSA / DLSA):',
    tollFree: '15100 (निःशुल्कम्, 24x7)',
    police: 'आरक्षकदलम्: 112',
    cyberCrime: 'अन्तर्जाल-अपराधः: 1930',
    women: 'महिला हेल्पलाइन: 1091',
    appTitle: 'न्यायवार्ता',
    appSubtitle: 'भारतीयनागरिकाणां कृते बहुभाषीय विधिकसहायकः (IPC → BNS)',
    apiOnline: 'सक्रियम् (Online)',
    tabChat: 'विधिकपरामर्शः (Legal Chat)',
    tabUpload: 'प्रलेखं योजयतु (Upload Document)',
    tabMatrix: 'विधिपरिवर्तनसारणी (Law Matrix)',
    ragTag: 'GraphRAG + Neo4j',
    chatHeader: 'न्यायवार्ता AI विधिकसहायकः',
    chatSubtitle: 'भारतीय न्याय संहिता (BNS) तथा निःशुल्क विधिकसाहाय्यम्',
    chatGreeting: 'नमस्ते! न्यायवार्ता अद्य भवतः कां सहायतां कर्तुं शक्नोति?',
    chatGreetingSub: 'स्वभाषायां लिखतु, वदतु वा स्वप्रलेखम् आरोपयतु। ज्ञानचित्रकं भवते मार्गदर्शनं दास्यति।',
    suggestedQueriesTitle: 'सुझाविताः विधिकप्रश्नाः',
    suggestedQueries: [
      {
        label: 'शून्य प्राथमिकी (BNSS 173)',
        text: 'प्राथमिकी (FIR) कथं पञ्जीकरणीया? शून्य-एफआईआर मान्या वा?',
      },
      {
        label: 'प्रतारणा (IPC 420 → BNS 318)',
        text: 'पुरातन IPC 420 तथा नूतन BNS 318 मध्ये कः भेदः अस्ति?',
      },
      {
        label: 'बन्धन-अधिकारः (BNSS 35)',
        text: 'BNSS धारा 35 अन्तर्गतं बन्धनसमये नागरिकस्य के अधिकाराः सन्ति?',
      },
      {
        label: 'निःशुल्क विधिकसाहाय्यम् (15100)',
        text: 'नागरिकाः NALSA 15100 द्वारा निःशुल्कं विधिकसाहाय्यं कथं प्राप्नुयुः?',
      },
    ],
    inputPlaceholder: 'स्वस्य विधिकप्रश्नं लिखतु अथवा वक्तुं ध्वनिग्राहकं नुदतु...',
    sendBtn: 'प्रेषयतु',
    listening: 'श्रूयते...',
    stopSend: 'विरामय प्रेषय च',
    attachDoc: 'प्रलेखं योजयतु (PDF / DOCX)',
    docAttached: 'प्रलेखः योजितः',
    matrixTitle: 'प्रमुखाः दण्डविधिपरिवर्तनाः (IPC → BNS)',
    matrixSubtitle: '१ जुलै २०२४ तः प्रवृत्ताः नूतनविधिधाराः:',
    matrixHeaders: {
      crime: 'अपराधः / विषयः',
      oldLaw: 'पुरातनधारा',
      newLaw: 'नूतनधारा (BNS)',
      note: 'प्रमुखपरिवर्तनानि',
    },
  },
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
