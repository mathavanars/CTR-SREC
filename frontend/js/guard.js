/** Keep signed-in pages in the saved five-step setup until it is complete. */

// This function checks the saved setup step before a signed-in page can open.
window.guard = async function guard(page) {
  const token = localStorage.getItem("arthmitra-token") || "";
  if (!token) return { allowed: false, authenticated: false };

  const response = await fetch(
    `${window.location.protocol}//${window.location.hostname}:8000/onboarding/status`,
    { headers: { Authorization: `Bearer ${token}` } },
  );
  if (response.status === 401) return { allowed: false, authenticated: false };
  if (!response.ok) throw new Error("We could not check your setup progress.");

  const status = await response.json();
  if (status.complete) return { allowed: true, authenticated: true, status };

  const pageOrder = {
    "money-details": 2,
    "edit-profile": 2,
    "retake-quiz": 3,
    "investment-choices": 4,
    "plan-review": 5,
  };
  const requestedOrder = pageOrder[page] || 6;
  const nextOrder = pageOrder[status.next_page] || 6;
  if (requestedOrder <= nextOrder) {
    return { allowed: true, authenticated: true, status };
  }
  return {
    allowed: false,
    authenticated: true,
    status,
    nextPage: status.next_page,
    message: `Let's finish your setup first (Step ${status.step_number} of 5).`,
  };
};
