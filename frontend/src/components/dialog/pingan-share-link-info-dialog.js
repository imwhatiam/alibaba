import React from 'react';
import PropTypes from 'prop-types';
import { Button, Modal, ModalHeader, ModalBody, ModalFooter } from 'reactstrap';
import { gettext } from '../../utils/constants';
import { Utils } from '../../utils/utils';

const propTypes = {
  toggle: PropTypes.func.isRequired,
  item: PropTypes.object.isRequired,
};

class PinganShareLinkInfoDialog extends React.Component {

  render() {
    let { item } = this.props;
    return (
      <Modal isOpen={true} toggle={this.props.toggle}>
        <ModalHeader toggle={this.props.toggle}>{gettext('共享链接信息')}</ModalHeader>
        <ModalBody>
          <div>
            {'文件大小：'}{Utils.bytesToSize(item.size)}<br/>
            {'创建时间：'}{item.created_at}<br/>
            {'过期时间：'}{item.expiration}<br/>
            {'链接：'}{item.share_link_url}
          </div>
        </ModalBody>
        <ModalFooter>
          <Button color="secondary" onClick={this.props.toggle}>{gettext('Close')}</Button>
        </ModalFooter>
      </Modal>
    );
  }
}

PinganShareLinkInfoDialog.propTypes = propTypes;

export default PinganShareLinkInfoDialog;
