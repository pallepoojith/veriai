chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({ id: "check-link", title: "Check this link with ClaimCheck", contexts: ["link"] });
  chrome.contextMenus.create({ id: "check-selection", title: "Check selected text with ClaimCheck", contexts: ["selection"] });
  chrome.contextMenus.create({ id: "check-page", title: "Check this page with ClaimCheck", contexts: ["page"] });
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  const pending = {
    url: info.linkUrl || tab?.url || "",
    text: info.selectionText || "",
  };
  await chrome.storage.local.set({ pending });
  try {
    await chrome.action.openPopup();
  } catch {
    chrome.action.setBadgeText({ text: "1" });
    chrome.action.setBadgeBackgroundColor({ color: "#2447d6" });
  }
});
