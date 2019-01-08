// document.addEventListener('DOMContentLoaded',function(event){
//   // array with texts to type in typewriter
//   var dataText = [  "Need Services ?", "Mentorship ?", "Freelancer?", "One Platform" ,"Connect To grow",];
  
//   // type one text in the typwriter
//   // keeps calling itself until the text is finished
//   function typeWriter(text, i, fnCallback) {
//     // chekc if text isn't finished yet
//     if (i < (text.length)) {
//       // add next character to h1
//      document.querySelector("h2").innerHTML = text.substring(0, i+1) +'<span class="new" aria-hidden="true"></span>';

//       // wait for a while and call this function again for next character
//       setTimeout(function() {
//         typeWriter(text, i + 1, fnCallback)
//       }, 100);
//     }
//     // text finished, call callback if there is a callback function
//     else if (typeof fnCallback == 'function') {
//       // call callback after timeout
//       setTimeout(fnCallback, 700);
//     }
//   }
//   // start a typewriter animation for a text in the dataText array
//    function StartTextAnimation(i) {
//      if (typeof dataText[i] == 'undefined'){
//         setTimeout(function() {
//           StartTextAnimation(0);
//         }, 20000);
//      }
//      // check if dataText[i] exists
//     if (i < dataText[i].length) {
//       // text exists! start typewriter animation
//      typeWriter(dataText[i], 0, function(){
//        // after callback (and whole text has been animated), start next text
//        StartTextAnimation(i + 1);
//      });
//     }
//   }
//   // start the text animation
//   StartTextAnimation(0);
// });

window.onscroll = () => {
  const nav = document.querySelector('#navbar');
  if(this.scrollY >= 60 && this.scrollY <= $(window).height()){ 
    nav.className = 'navbar navbar-expand-lg navbar-dark bg-new sticky-top';
    }
  else if(this.scrollY >= $(window).height()){
    nav.className = 'navbar navbar-expand-lg navbar-dark bg-new fixed-top';
  }
   else{ 
    nav.className = 'navbar navbar-expand-lg navbar-dark transparent';
  }
};

if ('serviceWorker' in navigator){
	navigator.serviceWorker
	.register('./serviceWorker.js')
	.then(function(){console.log("Service Worker registered");});

}


$(document).ready(function() {
  $(".container2").css(
    "background-image",
    "url(open.jpg)"
  );
  $(".container2").css(
    "background-size",
    "contain"
  );
  $(".container2").css(
      "background-position",
      "center"
    );
  $(".container2").css(
      "width",
      "120%"
    );
  $(".text-1").css({
    "background-color": "rgba(72, 72, 72, 1)",
    color: "white"
  });

  $(".text-1").hover(function() {
    $(".container2").css(
      "background-image",
      "url(image1.jpg)"
    );
    $(".container2").css(
      "background-size",
      "contain"
    );
    $(".container2").css(
      "background-position",
      "center"
    );
    $(".container2").css(
      "width",
      "128%"
    );
    $(".text-1").css({
      "background-color": "rgba(72, 72, 72, 1)",
      color: "white"
    });
    $(".text-2, .text-3, .text-4").css({
      "background-color": "rgba(255,255,255,0.6)",
      color: "black"
    });
  });

  $(".text-2").hover(function() {
    $(".container2").css(
      "background-image",
      "url(image2.jpg)"
    );
    $(".container2").css(
      "background-size",
      "contain"
    );
    $(".container2").css(
      "background-position",
      "center"
    );
    $(".container2").css(
      "width",
      "160%"
    );
    $(".text-2").css({
      "background-color": "rgba(72, 72, 72, 1)",
      color: "white"
    });
    $(".text-1, .text-3, .text-4").css({
      "background-color": "rgba(255,255,255,0.6)",
      color: "black"
    });
  });

  $(".text-3").hover(function() {
    $(".container2").css(
      "background-image",
      "url(image3.jpg)"
    );
    $(".container2").css(
      "background-size",
      "contain"
    );
    $(".container2").css(
      "background-position",
      "center"
    );
    $(".container2").css(
      "width",
      "200%"
    );
    $(".text-3").css({
      "background-color": "rgba(72, 72, 72, 1)",
      color: "white"
    });
    $(".text-1, .text-2, .text-4").css({
      "background-color": "rgba(255,255,255,0.6)",
      color: "black"
    });
  });

  $(".text-4").hover(function() {
    $(".container2").css(
      "background-image",
      "url(image4.jpg)"
    );
    $(".container2").css(
      "background-size",
      "contain"
    );
    $(".container2").css(
      "background-position",
      "center"
    );
    $(".container2").css(
      "width",
      "150%"
    );
    $(".text-4").css({
      "background-color": "rgba(72, 72, 72, 1)",
      color: "white"
    });
    $(".text-1, .text-2, .text-3").css({
      "background-color": "rgba(255,255,255,0.6)",
      color: "black"
    });
  });
});


// Trigger CSS animations on scroll.
// Detailed explanation can be found at http://www.bram.us/2013/11/20/scroll-animations/

// Looking for a version that also reverses the animation when
// elements scroll below the fold again?
// --> Check https://codepen.io/bramus/pen/vKpjNP

jQuery(function($) {

  // Function which adds the 'animated' class to any '.animatable' in view
  var doAnimations = function() {

    // Calc current offset and get all animatables
    var offset = $(window).scrollTop() + $(window).height(),
        $animatables = $('.animatable');

    // Unbind scroll handler if we have no animatables
    if ($animatables.length == 0) {
      $(window).off('scroll', doAnimations);
    }

    // Check all animatables and animate them if necessary
    $animatables.each(function(i) {
       var $animatable = $(this);
      if (($animatable.offset().top + $animatable.height() - 20) < offset ) {
        $animatable.removeClass('animatable').addClass('animated');
      }
     
    });

  };

  // Hook doAnimations on scroll, and trigger a scroll
  $(window).on('scroll', doAnimations);
  $(window).trigger('scroll');

});

$(window).scroll(function() {
    if ($(this).scrollTop() > 50 ) {
        $('.scrolltop:hidden').stop(true, true).fadeIn();
    } else {
        $('.scrolltop').stop(true, true).fadeOut();
    }
});
$(function(){$(".scroll").click(function(){$("html,body").animate({scrollTop:$(".thetop").offset().top},"1000");return false})})

$(window).scroll(function() {
    if ($(this).scrollTop() >= ($(document).height() - $(window).height()) ) {
        $('.signature:hidden').stop(true, true).fadeIn();
    } else {
        $('.signature').stop(true, true).fadeOut();
    }
});




// Customer Reviews
const app = new Vue({
  el: '#app',
  data: {
    reviews: [],
    products: []
  },
  created () {
  fetch('https://api.myjson.com/bins/6cyk0')
    .then(response => response.json())
    .then(json => {
      this.reviews = json
      // console.log(this.reviews)
    })
  }
});