$(document).ready(function(){
    $("#welcome-user").modal({
show:false,
backdrop:'static'
});
        $('#welcome-user').modal('show');
    $('#select_multi_product').multiselect({
        columns: 1,
        placeholder: 'Search by item name',
        search: true,
        // selectAll: true
    });
     console.log("sssssssssssssssssssssssss")
    $('#sidebarCollapse').on('click', function () {
        console.log("sssssssssssssssssssssssss")
                $('#sidebar').toggleClass('active');
                $('.main_logo').toggleClass('active');

                 $('#wrapwrap').toggleClass('right_sidebar');                
            });
});



function openCity(evt, cityName) {
  var i, tabcontent, tablinks;
  tabcontent = document.getElementsByClassName("tabcontent");
  for (i = 0; i < tabcontent.length; i++) {
    tabcontent[i].style.display = "none";
  }
  tablinks = document.getElementsByClassName("tablinks");
  for (i = 0; i < tablinks.length; i++) {
    tablinks[i].className = tablinks[i].className.replace(" active", "");
  }
  document.getElementById(cityName).style.display = "block";
  evt.currentTarget.className += " active";
}



