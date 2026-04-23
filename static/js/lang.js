const translations = { /* KEEP YOUR WHOLE TRANSLATIONS OBJECT EXACTLY AS IS */ };

function setLanguage(lang) {
    localStorage.setItem("siteLanguage", lang);

    document.documentElement.lang = lang;
    document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
    document.body.classList.toggle("rtl", lang === "ar");

    document.querySelectorAll("[data-i18n]").forEach((el) => {
        const key = el.getAttribute("data-i18n");
        if (translations[lang] && translations[lang][key]) {
            el.textContent = translations[lang][key];
        }
    });

    document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
        const key = el.getAttribute("data-i18n-placeholder");
        if (translations[lang] && translations[lang][key]) {
            el.placeholder = translations[lang][key];
        }
    });

    const current = document.getElementById("currentLanguage");
    if (current) {
        current.textContent = lang === "ar" ? "العربية" : "English";
    }
}

document.addEventListener("DOMContentLoaded", function () {

    const saved = localStorage.getItem("siteLanguage") || "en";
    setLanguage(saved);

    // =========================
    // LANGUAGE SWITCHER
    // =========================
    const toggle = document.getElementById("languageToggle");
    const menu = document.getElementById("languageMenu");

    if (toggle && menu) {
        toggle.addEventListener("click", function (e) {
            e.stopPropagation();
            menu.classList.toggle("show-language-menu");
        });

        document.addEventListener("click", function () {
            menu.classList.remove("show-language-menu");
        });

        menu.addEventListener("click", function (e) {
            e.stopPropagation();
        });

        document.querySelectorAll(".language-option").forEach((btn) => {
            btn.addEventListener("click", function () {
                const lang = this.getAttribute("data-lang");
                setLanguage(lang);
                menu.classList.remove("show-language-menu");
            });
        });
    }

    // =========================
    // CHATBOT
    // =========================
    const chatInput = document.getElementById("chatInput");
    const chatMessages = document.getElementById("chatMessages");

    let lastBotReply = "";

    function getCurrentLang() {
        return localStorage.getItem("siteLanguage") || "en";
    }

    function addMessage(text, type) {
        const div = document.createElement("div");

        // ✅ FIXED LINE
        div.className = `chatbot-message ${type}`;

        div.textContent = text;
        chatMessages.appendChild(div);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function speakText(text) {
        if (!("speechSynthesis" in window)) return;

        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = getCurrentLang() === "ar" ? "ar-SA" : "en-US";

        window.speechSynthesis.cancel();
        window.speechSynthesis.speak(utterance);
    }

    async function sendMessageToServer(message) {
        addMessage(message, "user");

        try {
            const response = await fetch("/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: message })
            });

            const data = await response.json();

            const reply = data.response || "No response";
            addMessage(reply, "bot");

            lastBotReply = reply;
            speakText(reply);

        } catch (error) {
            addMessage("Server error", "bot");
        }
    }

    window.sendMessage = function () {
        const msg = chatInput.value.trim();
        if (!msg) return;

        chatInput.value = "";
        sendMessageToServer(msg);
    };

    if (chatInput) {
        chatInput.addEventListener("keypress", function (e) {
            if (e.key === "Enter") {
                sendMessage();
            }
        });
    }

    // =========================
    // VOICE INPUT 🎤
    // =========================
    const micBtn = document.getElementById("chatMicBtn");
    let recognition;

    if ("webkitSpeechRecognition" in window || "SpeechRecognition" in window) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRecognition();

        recognition.onresult = function (event) {
            const text = event.results[0][0].transcript;
            chatInput.value = text;
            sendMessage();
        };
    }

    if (micBtn && recognition) {
        micBtn.addEventListener("click", function () {
            recognition.start();
        });
    }

    // =========================
    // SPEAK BUTTON 🔊
    // =========================
    const speakBtn = document.getElementById("chatSpeakBtn");

    if (speakBtn) {
        speakBtn.addEventListener("click", function () {
            if (lastBotReply) {
                speakText(lastBotReply);
            }
        });
    }

});