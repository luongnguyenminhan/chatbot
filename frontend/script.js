document.addEventListener('DOMContentLoaded', () => {
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const chatLog = document.getElementById('chat-log');
    const emojiButton = document.getElementById('emoji-button');
    const newConversationBtn = document.getElementById('new-conversation-btn');
    const conversationList = document.getElementById('conversation-list');
    const currentConversationTitle = document.getElementById('current-conversation-title');
    const renameConversationBtn = document.getElementById('rename-conversation-btn');
    const deleteConversationBtn = document.getElementById('delete-conversation-btn');
    const renameModal = document.getElementById('rename-modal');
    const closeModal = document.querySelector('.close-modal');
    const newTitleInput = document.getElementById('new-title-input');
    const saveTitleBtn = document.getElementById('save-title-btn');

    // API base URL
    const API_BASE_URL = 'http://127.0.0.1:8000/api';

    // State for tracking conversations
    let currentConversationId = null;
    let conversations = [];

    // Include marked.js library for markdown rendering
    const markedScript = document.createElement('script');
    markedScript.src = 'https://cdn.jsdelivr.net/npm/marked@4.0.0/marked.min.js';
    document.head.appendChild(markedScript);

    // Function to safely render markdown or plain text
    const renderMarkdown = (text) => {
        try {
            if (typeof marked !== 'undefined') {
                return marked.parse(text);
            }
            return text;
        } catch (error) {
            console.error('Error rendering markdown:', error);
            return text;
        }
    };

    // Function to get current timestamp in HH:MM AM/PM format
    const getCurrentTimestamp = () => {
        const now = new Date();
        const hours = now.getHours();
        const minutes = now.getMinutes();
        const ampm = hours >= 12 ? 'PM' : 'AM';
        const formattedHours = hours % 12 || 12;
        const formattedMinutes = minutes < 10 ? `0${minutes}` : minutes;
        return `${formattedHours}:${formattedMinutes} ${ampm}`;
    };

    // Function to display a message in the chat
    const displayMessage = (message, sender) => {
        // Create message container
        const messageContainer = document.createElement('div');
        messageContainer.classList.add('message-container', sender === 'user' ? 'user' : 'assistant');

        // Create message div
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', sender === 'user' ? 'user-message' : 'assistant-message');

        // Create message text div
        const messageTextDiv = document.createElement('div');
        messageTextDiv.classList.add('message-text');

        // Set message content
        if (sender === 'user') {
            messageTextDiv.textContent = message;
        } else {
            // Clean up any hidden conversation ID markers
            const cleanMessage = message.replace(/\n<!--conversation_id:[a-f0-9-]+-->/g, '');
            messageTextDiv.innerHTML = renderMarkdown(cleanMessage);
            // Make links open in a new tab
            const links = messageTextDiv.querySelectorAll('a');
            links.forEach(link => {
                link.setAttribute('target', '_blank');
                link.setAttribute('rel', 'noopener noreferrer');
            });
        }

        // Create and add timestamp
        const timestampDiv = document.createElement('div');
        timestampDiv.classList.add('timestamp');
        timestampDiv.textContent = getCurrentTimestamp();

        messageDiv.appendChild(messageTextDiv);
        messageDiv.appendChild(timestampDiv);

        // Add avatar and assemble structure
        if (sender === 'assistant') {
            const avatar = document.createElement('img');
            avatar.classList.add('avatar');
            avatar.src = 'assistant-avatar.png'; // Ensure this image exists
            avatar.alt = 'Assistant Avatar';
            messageContainer.appendChild(avatar);
            messageContainer.appendChild(messageDiv);
        } else {
            messageContainer.appendChild(messageDiv);
            const avatar = document.createElement('img');
            avatar.classList.add('avatar');
            avatar.src = 'user-avatar.png'; // Ensure this image exists
            avatar.alt = 'User Avatar';
            messageContainer.appendChild(avatar);
        }

        chatLog.appendChild(messageContainer);
        chatLog.scrollTop = chatLog.scrollHeight;
    };

    // Function to create a new conversation
    const createNewConversation = async (title = 'New Conversation') => {
        try {
            const response = await fetch(`${API_BASE_URL}/conversations`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const conversation = await response.json();
            currentConversationId = conversation.conversation_id;
            currentConversationTitle.textContent = conversation.title;

            // Update conversations list
            await loadConversations();

            // Clear chat log
            chatLog.innerHTML = '';

            // Display welcome message
            displayMessage("Hello! How can I assist you today?", "assistant");

            return conversation;
        } catch (error) {
            console.error('Error creating conversation:', error);
            alert('Failed to create a new conversation. Please try again.');
        }
    };

    // Function to load all conversations
    const loadConversations = async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/conversations`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            conversations = await response.json();
            renderConversationList();

            return conversations;
        } catch (error) {
            console.error('Error loading conversations:', error);
            alert('Failed to load conversations. Please refresh the page.');
        }
    };

    // Function to render the conversation list
    const renderConversationList = () => {
        conversationList.innerHTML = '';

        // Sort conversations by updated_at (newest first)
        const sortedConversations = [...conversations].sort((a, b) =>
            new Date(b.updated_at) - new Date(a.updated_at)
        );

        sortedConversations.forEach(conversation => {
            const item = document.createElement('div');
            item.classList.add('conversation-item');
            if (conversation.conversation_id === currentConversationId) {
                item.classList.add('active');
            }

            item.textContent = conversation.title;
            item.dataset.id = conversation.conversation_id;

            item.addEventListener('click', () => selectConversation(conversation.conversation_id));

            conversationList.appendChild(item);
        });
    };

    // Function to select and load a conversation
    const selectConversation = async (conversationId) => {
        currentConversationId = conversationId;

        // Find the conversation object
        const conversation = conversations.find(c => c.conversation_id === conversationId);
        if (conversation) {
            currentConversationTitle.textContent = conversation.title;
        }

        // Update UI to show this is the active conversation
        renderConversationList();

        // Clear chat log
        chatLog.innerHTML = '';

        // In a real app, you'd load the conversation history here
        // For now, we'll just show a welcome back message
        displayMessage("Welcome back! How can I help you with this conversation?", "assistant");
    };

    // Function to rename the current conversation
    const renameConversation = async () => {
        if (!currentConversationId) return;

        const newTitle = newTitleInput.value.trim();
        if (!newTitle) return;

        try {
            const response = await fetch(`${API_BASE_URL}/conversations/${currentConversationId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title: newTitle })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const updatedConversation = await response.json();
            currentConversationTitle.textContent = updatedConversation.title;

            // Update in our local list
            const index = conversations.findIndex(c => c.conversation_id === currentConversationId);
            if (index !== -1) {
                conversations[index] = updatedConversation;
            }

            renderConversationList();
            closeRenameModal();

        } catch (error) {
            console.error('Error renaming conversation:', error);
            alert('Failed to rename the conversation. Please try again.');
        }
    };

    // Function to delete the current conversation
    const deleteConversation = async () => {
        if (!currentConversationId) return;

        if (!confirm("Are you sure you want to delete this conversation?")) return;

        try {
            const response = await fetch(`${API_BASE_URL}/conversations/${currentConversationId}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            // Remove from our local list
            conversations = conversations.filter(c => c.conversation_id !== currentConversationId);

            // Select another conversation or create a new one
            if (conversations.length > 0) {
                selectConversation(conversations[0].conversation_id);
            } else {
                createNewConversation();
            }

        } catch (error) {
            console.error('Error deleting conversation:', error);
            alert('Failed to delete the conversation. Please try again.');
        }
    };

    // Function to send a message and handle streaming response
    const sendMessage = async () => {
        const messageText = messageInput.value.trim();
        if (!messageText) return;

        // Create a new conversation if we don't have one
        if (!currentConversationId) {
            await createNewConversation();
        }

        // Display user message
        displayMessage(messageText, 'user');
        messageInput.value = '';

        try {
            const response = await fetch(`${API_BASE_URL}/${currentConversationId}/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    messages: [{
                        role: 'user',
                        content: [{ type: 'text', text: messageText }]
                    }]
                })
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`HTTP error! status: ${response.status}, body: ${errorText}`);
            }

            // Set up assistant message structure
            const messageContainer = document.createElement('div');
            messageContainer.classList.add('message-container', 'assistant');

            const avatar = document.createElement('img');
            avatar.classList.add('avatar');
            avatar.src = 'assistant-avatar.png';
            avatar.alt = 'Assistant Avatar';

            const messageDiv = document.createElement('div');
            messageDiv.classList.add('message', 'assistant-message');

            const messageTextDiv = document.createElement('div');
            messageTextDiv.classList.add('message-text');

            const timestampDiv = document.createElement('div');
            timestampDiv.classList.add('timestamp');
            timestampDiv.textContent = getCurrentTimestamp();

            messageDiv.appendChild(messageTextDiv);
            messageDiv.appendChild(timestampDiv);
            messageContainer.appendChild(avatar);
            messageContainer.appendChild(messageDiv);
            chatLog.appendChild(messageContainer);
            chatLog.scrollTop = chatLog.scrollHeight;

            // Process streaming response
            let messageBuffer = '';
            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const { done, value } = await reader.read();
                if (done) {
                    // Clean the conversation ID hidden marker for display
                    const cleanMessage = messageBuffer.replace(/\n<!--conversation_id:[a-f0-9-]+-->/g, '');
                    // Finalize with markdown rendering
                    messageTextDiv.innerHTML = renderMarkdown(cleanMessage);
                    const links = messageTextDiv.querySelectorAll('a');
                    links.forEach(link => {
                        link.setAttribute('target', '_blank');
                        link.setAttribute('rel', 'noopener noreferrer');
                    });
                    chatLog.scrollTop = chatLog.scrollHeight;
                    break;
                }

                // Decode and parse chunk
                const chunk = decoder.decode(value, { stream: true });
                let textChunk = '';
                const regex = /\d+:"([^"]*)"/g;
                let match;
                let foundMatch = false;

                while ((match = regex.exec(chunk)) !== null) {
                    foundMatch = true;
                    textChunk += match[1];
                }

                if (!foundMatch) {
                    try {
                        const lines = chunk.split('\n').filter(line => line.trim());
                        for (const line of lines) {
                            if (line.startsWith('data:')) {
                                const jsonData = line.substring(5).trim();
                                const parsedData = JSON.parse(jsonData);
                                if (parsedData.type === 'text') {
                                    textChunk += parsedData.text;
                                }
                            } else {
                                const parsedChunk = JSON.parse(line);
                                if (parsedChunk.type === 'data' && parsedChunk.data) {
                                    textChunk += parsedChunk.data;
                                }
                            }
                        }
                    } catch (e) {
                        const indexContentRegex = /(\d+):(.+)/g;
                        let indexContentMatch;
                        let foundIndexContent = false;

                        while ((indexContentMatch = indexContentRegex.exec(chunk)) !== null) {
                            foundIndexContent = true;
                            textChunk += indexContentMatch[2];
                        }

                        if (!foundIndexContent) {
                            textChunk += chunk;
                        }
                    }
                }

                // Update message progressively
                messageBuffer += textChunk;
                // Clean hidden markers for display
                const cleanBuffer = messageBuffer.replace(/\n<!--conversation_id:[a-f0-9-]+-->/g, '');
                messageTextDiv.textContent = cleanBuffer;
                chatLog.scrollTop = chatLog.scrollHeight;
            }

            // Refresh the conversation list to update timestamps
            loadConversations();

        } catch (error) {
            console.error('Error sending message:', error);
            const errorMessage = error instanceof TypeError ? 'Error: Network error. Please check your connection.' : `Error: ${error.message}`;
            displayMessage(errorMessage, 'assistant');
        }
    };

    // Modal functions
    const openRenameModal = () => {
        renameModal.style.display = 'block';
        newTitleInput.value = currentConversationTitle.textContent;
        newTitleInput.focus();
    };

    const closeRenameModal = () => {
        renameModal.style.display = 'none';
    };

    // Event listeners
    sendButton.addEventListener('click', sendMessage);
    messageInput.addEventListener('keypress', (event) => {
        if (event.key === 'Enter') {
            sendMessage();
        }
    });

    newConversationBtn.addEventListener('click', () => createNewConversation());
    renameConversationBtn.addEventListener('click', openRenameModal);
    deleteConversationBtn.addEventListener('click', deleteConversation);

    closeModal.addEventListener('click', closeRenameModal);
    saveTitleBtn.addEventListener('click', renameConversation);

    newTitleInput.addEventListener('keypress', (event) => {
        if (event.key === 'Enter') {
            renameConversation();
        }
    });

    // Hide modal when clicking outside
    window.addEventListener('click', (event) => {
        if (event.target === renameModal) {
            closeRenameModal();
        }
    });

    // Emoji button functionality
    if (emojiButton) {
        emojiButton.addEventListener('click', () => {
            const emojis = ['😊', '👍', '🎉', '🤔', '👋', '❤️', '😂', '🙏', '👏', '🔥'];
            const randomEmoji = emojis[Math.floor(Math.random() * emojis.length)];
            messageInput.value += randomEmoji;
            messageInput.focus();
        });
    }

    // Initialize: load conversations or create a new one
    const init = async () => {
        await loadConversations();
        if (conversations && conversations.length > 0) {
            selectConversation(conversations[0].conversation_id);
        } else {
            createNewConversation();
        }
    };

    init();
});