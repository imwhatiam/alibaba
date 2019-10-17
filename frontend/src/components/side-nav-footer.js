import React from 'react';
import { gettext, siteRoot } from '../utils/constants';
import ModalPortal from './modal-portal';
import AboutDialog from './dialog/about-dialog';

class SideNavFooter extends React.Component {

  constructor(props) {
    super(props);
    this.state = {
      isAboutDialogShow: false,
    };
  }

  onAboutDialogToggle = () => {
    this.setState({isAboutDialogShow: !this.state.isAboutDialogShow});
  }

  render() {
    return (
      <div className="side-nav-footer pl-3" style={{fontSize:'12px'}}>
        <a href={siteRoot + 'help/'} target="_blank" rel="noopener noreferrer" className="item mr-4">帮助</a>
        <a className="item cursor-pointer mr-4" onClick={this.onAboutDialogToggle}>{gettext('About')}</a>
        <a className="item cursor-pointer mr-4" href="#">FAQ about pafile</a>
        <a className="item cursor-pointer mr-1" href="http://fcloud.paic.com.cn/f/e176568aa7/?raw=1">权限申请/注销</a>
        {/* <a href={siteRoot + 'download_client_program/'} className="item last-item">
          <span aria-hidden="true" className="sf2-icon-monitor vam"></span>{' '}
          <span className="vam">{gettext('Clients')}</span>
        </a> */}
        {this.state.isAboutDialogShow &&
          <ModalPortal>
            <AboutDialog onCloseAboutDialog={this.onAboutDialogToggle} />
          </ModalPortal>
        }
      </div>
    );
  }
}

export default SideNavFooter;
