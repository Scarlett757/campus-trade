// 绑定点击事件
function bindEmailCodeClick(){
    // #：在 jQuery/CSS 中是ID 选择器的标识，专门用来选中页面中 id 属性等于指定值的元素。
    //     对比理解：
    // $(".class-name")：. 是类选择器，选中 class 为 class-name 的元素；
    // $("div")：标签选择器，选中所有 div 元素。
    // 通过 jQuery 选中页面中 id 为 send-code 的元素，给这个元素绑定一个点击事件；当用户点击这个元素时，执行后面匿名函数里的代码
    $("#send-code").click(function(event){
        event.preventDefault(); // 阻止默认行为

        // 将当前button转换为jquiry对象
        let that=$(this);

        // 1. 获取用户输入的邮箱，即：获取输入框（对应id为：reg-email）中对应内容,.val()即可获取对应的值
        let email=$("#reg-email").val();
        // 2. 验证邮箱是否合法
        let emailReg = /^[a-zA-Z0-9_-]+@[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+)+$/;
        if(!emailReg.test(email)){
            alert("Please enter valid email");
            return;
        }

        // 为保证倒计时期间用户不再能点击获取验证嘛，取消点击事件
        that.off('click');

        // 3. 倒计时
        let countdown=6;
        that.text(countdown+"s");
        // 定义一个计时器
        let timer=setInterval(function(){
            countdown--;
            that.text(countdown+"s");
            if(countdown<0){
                that.text('获取验证码');
                clearInterval(timer);// 清空倒计时
                bindEmailCodeClick();//重新绑定点击事件
            }
        }, 1000)

        // 4. 发送ajax请求
        // 这段代码是前端通过 jQuery 发送一个 GET 类型的 AJAX 请求，目标是调用你之前写的后端 /email/code 接口，把用户输入的 email 作为参数传递给后端，并在请求成功后，把后端返回的结果打印到浏览器控制台。
        // AJAX 的核心作用是：前端在不刷新页面的情况下，异步向后端发送请求并获取数据（比如你点击 “发送验证码” 按钮，页面不刷新，但能把邮箱传给后端）
        $.get({
            url:"/email/code",
            data:{email:email},
            success:function(result){
                console.log(result);
            }

        })

    })
}

function bindRegisterEvent(){
$("#submit-btn").click(function(event){
    event.preventDefault();
    let email=$("#reg-email").val();
    let code=$("#reg-code").val();
    let username=$("#reg-username").val();
    let password=$("#reg-password").val();
    let confirm_password=$("#reg-confirm-password").val();
    if(!email){
            alert("邮箱不能为空！");
            return;
        }
        if(!code){
            alert("验证码不能为空！");
            return;
        }
        if(!username){
            alert("用户名不能为空！");
            return;
        }
        if(!password){
            alert("密码不能为空！");
            return;
        }
        if(!confirm_password){
            alert("确认密码不能为空！");
            return;
        }

    if(confirm_password!=password){
        alert("两次密码不一致！");
        return;
    }

    $.post({
        url:"/register",
        data:{email,code,username,password},
        success:function(resp){
            if(resp['result']==true) {
                window.location = '/login';
            }else{
                let message=rep['message'];
                alert(message);
            }
        }
    })
})
}

// 整个网页加载完成后
$(function() {
    bindEmailCodeClick();
    bindRegisterEvent();
})