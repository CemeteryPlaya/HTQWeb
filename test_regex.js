const msg = "Failed to execute 'setRemoteDescription' on 'RTCPeerConnection': Failed to set remote offer sdp: Session error code: ERROR_CONTENT. Session error description: The m= section with mid='2' should be rejected..";
const pattern1 = /mid=['"]?([^'".\s]+)['"]?\s+should be rejected/i;
const match1 = msg.match(pattern1);
console.log("Match 1:", match1 ? match1[1] : "null");

const pattern2 = /mid=['"]?([^'".\s]+)['"]?.+rejected/i;
const match2 = msg.match(pattern2);
console.log("Match 2:", match2 ? match2[1] : "null");
