const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

export const api = {
    async get(endpoint) {
        const res = await fetch(`${API_BASE}${endpoint}`);
        if (!res.ok) throw new Error(`API Error: ${res.statusText}`);
        return res.json();
    },

    async post(endpoint, data) {
        const isFormData = data instanceof FormData;
        const options = {
            method: 'POST',
            body: isFormData ? data : JSON.stringify(data),
            headers: isFormData ? {} : { 'Content-Type': 'application/json' },
        };

        const res = await fetch(`${API_BASE}${endpoint}`, options);
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: res.statusText }));
            throw new Error(err.detail || `API Error: ${res.statusText}`);
        }
        return res.json();
    },

    async patch(endpoint, data) {
        const res = await fetch(`${API_BASE}${endpoint}`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data),
        });
        if (!res.ok) throw new Error(`API Error: ${res.statusText}`);
        return res.json();
    }
};
