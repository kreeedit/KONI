function toggle3(contentDiv) {
        if (contentDiv.constructor == Array) {
                for(i=0; i < contentDiv.length; i++) {
                     toggle(contentDiv[i]);
                }
        }
        else {
               toggle(contentDiv);
        }
}

function toggle(showHideDiv) {
	var ele = document.getElementById(showHideDiv);
	if(ele.style.display == "block") {
    	ele.style.display = "none";
  	}
	else {
		ele.style.display = "block";
	}
} 