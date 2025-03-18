const handleLogin = async () => {
  setLoading(true);
  
  try {
    const success = await login(values.username, values.password);
    
    if (success) {
      // 登录成功后更新权限信息
      await updatePermissions();
      
      // 检查密码是否过期
      const passwordExpired = await checkPasswordExpired();
      
      // 如果密码过期，跳转到修改密码页面
      if (passwordExpired) {
        navigate('/change-password');
      } else {
        // 否则跳转到首页
        navigate('/dashboard');
      }
    }
  } catch (error) {
    console.error('登录失败', error);
    message.error('登录失败，请检查用户名和密码');
  } finally {
    setLoading(false);
  }
}; 