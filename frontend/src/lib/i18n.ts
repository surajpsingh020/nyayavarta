/**
 * UI Localization (i18n) dictionary for Nyayavarta.
 * Translates header, navigation tabs, user personas, chat interface, and suggested queries.
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
  personaHeader: string;
  personas: {
    general: { title: string; desc: string };
    student: { title: string; desc: string };
    senior_citizen: { title: string; desc: string };
    professional: { title: string; desc: string };
  };
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
  matrixTitle: string;
  matrixSubtitle: string;
  matrixHeaders: {
    crime: string;
    oldLaw: string;
    newLaw: string;
    note: string;
  };
}

export const I18N_STRINGS: Record<string, UITranslation> = {
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
    tabUpload: 'दस्तावेज़ जोड़ें (Document Ingestion)',
    tabMatrix: 'कानून परिवर्तन चार्ट (Law Matrix)',
    ragTag: 'हाइब्रिड RAG + Neo4j',
    personaHeader: 'उपयोगकर्ता प्रोफ़ाइल (User Persona)',
    personas: {
      general: {
        title: 'आम नागरिक (General Citizen)',
        desc: 'दैनिक अधिकार, सरल उपाय और त्वरित कदम',
      },
      student: {
        title: 'विद्यार्थी (Student / Academic)',
        desc: 'शैक्षणिक विश्लेषण, वैधानिक तर्क और परिभाषाएं',
      },
      senior_citizen: {
        title: 'वरिष्ठ नागरिक (Senior Citizen)',
        desc: 'सहानुभूतिपूर्ण, सरल मार्गदर्शन और वरिष्ठ कल्याण अधिकार',
      },
      professional: {
        title: 'पेशेवर (Professional)',
        desc: 'औपचारिक अनुपालन, प्रक्रियात्मक समयसीमा और कानूनी दायित्व',
      },
    },
    chatHeader: 'न्यायवार्ता AI कानूनी सहायक',
    chatSubtitle: 'भारतीय दंड संहिता (IPC) → भारतीय न्याय संहिता (BNS) एवं विधिक सहायता',
    chatGreeting: 'नमस्ते! न्यायवार्ता आज आपकी क्या सहायता कर सकता है?',
    chatGreetingSub: 'अपनी भाषा में लिखें या बोलने के लिए माइक पर क्लिक करें। हमारा कानूनी RAG पुराने कानूनों को नए BNS प्रावधानों में बदल कर सहायता प्रदान करेगा।',
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
    inputPlaceholder: 'अपना कानूनी प्रश्न यहां लिखें या बोलने के लिए माइक पर क्लिक करें...',
    sendBtn: 'भेजें (Send)',
    listening: 'ध्वनि रिकॉर्ड हो रही है...',
    stopSend: 'रोकें और भेजें',
    matrixTitle: 'प्रमुख आपराधिक कानून परिवर्तन (IPC → BNS / CrPC → BNSS / IEA → BSA)',
    matrixSubtitle: '1 जुलाई 2024 से लागू नए कानूनों के प्रमुख धारा परिवर्तन:',
    matrixHeaders: {
      crime: 'अपराध / विषय',
      oldLaw: 'पुराना कानून (Old Section)',
      newLaw: 'नया कानून 2023 (New Section)',
      note: 'प्रमुख बदलाव / टिप्पणी',
    },
  },
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
    tabUpload: 'Document Ingestion',
    tabMatrix: 'Law Transition Matrix',
    ragTag: 'Hybrid RAG + Neo4j',
    personaHeader: 'User Persona / Consultation Profile',
    personas: {
      general: {
        title: 'General Citizen',
        desc: 'Everyday rights, simple remedies, and immediate steps',
      },
      student: {
        title: 'Student / Academic',
        desc: 'Educational breakdown, statutory logic, and definitions',
      },
      senior_citizen: {
        title: 'Senior Citizen',
        desc: 'Compassionate, simple guidance and elder welfare rights',
      },
      professional: {
        title: 'Professional',
        desc: 'Formal compliance, procedural timelines, and liabilities',
      },
    },
    chatHeader: 'Nyayavarta AI Assistant',
    chatSubtitle: 'Indian Penal Code (IPC) → Bharatiya Nyaya Sanhita (BNS) & Legal Aid',
    chatGreeting: 'Namaste! How can Nyayavarta assist you today?',
    chatGreetingSub: 'Type in your language or click the microphone to speak. Our hybrid legal RAG will map old IPC laws to new BNS provisions and provide step-by-step aid.',
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
    inputPlaceholder: 'Type your legal query here or click the microphone to speak...',
    sendBtn: 'Send',
    listening: 'Recording Voice Query...',
    stopSend: 'Stop & Send',
    matrixTitle: 'Key Criminal Law Transitions (IPC → BNS / CrPC → BNSS / IEA → BSA)',
    matrixSubtitle: 'Effective July 1, 2024, Indian criminal law transitioned to modernized statutes:',
    matrixHeaders: {
      crime: 'Subject / Crime',
      oldLaw: 'Old Law Section',
      newLaw: 'New Law Section (2023)',
      note: 'Key Transition Note',
    },
  },
};

export function getUITranslations(langCode: string): UITranslation {
  return I18N_STRINGS[langCode] || I18N_STRINGS['hi'] || I18N_STRINGS['en'];
}
