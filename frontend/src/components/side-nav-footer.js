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
      <div className="side-nav-footer">
        <a className="item cursor-pointer" onClick={this.onAboutDialogToggle}>{gettext('About')}</a>
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
