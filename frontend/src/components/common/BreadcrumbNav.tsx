import React from 'react';
import { Breadcrumb, Button, Flex } from 'antd';
import { useNavigate, Link } from 'react-router-dom';
import { ArrowLeftOutlined, HomeOutlined } from '@ant-design/icons';

interface BreadcrumbItem {
  title: string;
  path?: string;
}

interface BreadcrumbNavProps {
  items: BreadcrumbItem[];
  showBackButton?: boolean;
  backButtonText?: string;
  onBack?: () => void;
}

const BreadcrumbNav: React.FC<BreadcrumbNavProps> = ({
  items,
  showBackButton = true,
  backButtonText = '返回',
  onBack,
}) => {
  const navigate = useNavigate();
  
  const handleBack = () => {
    if (onBack) {
      onBack();
    } else {
      navigate(-1);
    }
  };

  return (
    <Flex align="center" justify="space-between" style={{ marginBottom: 16 }}>
      <Breadcrumb items={[
        {
          title: (
            <Link to="/dashboard">
              <HomeOutlined /> 首页
            </Link>
          ),
        },
        ...items.map((item) => ({
          title: item.path ? (
            <Link to={item.path}>
              {item.title}
            </Link>
          ) : (
            item.title
          ),
        })),
      ]} />
      
      {showBackButton && (
        <Button icon={<ArrowLeftOutlined />} onClick={handleBack}>
          {backButtonText}
        </Button>
      )}
    </Flex>
  );
};

export default BreadcrumbNav; 