const API = {
  async getStatus() {
    try {
      const res = await fetch('/api/status');
      return await res.json();
    } catch (e) {
      console.error('Error fetching status:', e);
      return null;
    }
  },

  async getEvents(limit = 20) {
    try {
      const res = await fetch(`/api/events?limit=${limit}`);
      return await res.json();
    } catch (e) {
      console.error('Error fetching events:', e);
      return [];
    }
  },

  async getConfig() {
    try {
      const res = await fetch('/api/config');
      return await res.json();
    } catch (e) {
      console.error('Error fetching config:', e);
      return null;
    }
  }
};
