
$(document).ready(function(){
  $(window).scroll(function(){
  	var scroll = $(window).scrollTop();
	  if (scroll > 100) {
	    $(".bg-new").css("background" , "#fff");
	  }

	  else{
		  $(".bg-new").css("background" , "transparent");  	
	  }
  })
})