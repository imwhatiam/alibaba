import React from 'react';
import { gettext, siteRoot } from '../utils/constants';
import ModalPortal from './modal-portal';
import AboutDialog from './dialog/about-dialog';
import { pinganFaqUrl, pinganHelpUrl, pinganPermissionHelpUrl } from '../utils/constants';

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
        <a href={pinganHelpUrl} target="_blank" rel="noopener noreferrer" className="item mr-4">帮助</a>
        <a className="item cursor-pointer mr-4" onClick={this.onAboutDialogToggle}>{gettext('About')}</a>
        <a className="item cursor-pointer mr-4" href={pinganFaqUrl}>FAQ about pafile</a>
        <a className="item cursor-pointer mr-1" target="_blank" href={pinganPermissionHelpUrl}>权限申请/注销</a>
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
